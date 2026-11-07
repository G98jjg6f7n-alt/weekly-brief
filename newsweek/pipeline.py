"""主流程 v2：抓取 → 预筛 → 模型精选 → 正文 → 卡片与评论 → 深度观察 → 渲染。"""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import re
import time
from datetime import datetime

from . import cluster, rank, summarize
from . import media
from .extract import fetch_article
from .fetch import Article, detect_proxy, fetch_all, set_proxy
from .llm import usage_summary
from .util import TZ, fmt_cn, week_label, week_range

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

JUNK = re.compile(
    r"(明星|绯闻|八卦|恋情|官宣恋情|结婚|离婚|婚纱|写真|整容|网红|带货|彩票|中奖|双色球|"
    r"开奖|运势|星座|风水|算命|灵异|猎奇|视频欣赏|组图|图集)"
)


def load_config(path: str | None = None) -> dict:
    with open(path or os.path.join(ROOT, "config.json"), encoding="utf-8") as fh:
        return json.load(fh)


def log(msg: str, quiet: bool = False) -> None:
    if not quiet:
        print(msg, flush=True)


def load_profile(cfg: dict) -> dict:
    """读取可选的个性化档案：栏目加权、关键词加权、长期观察清单。"""
    out = os.path.join(ROOT, cfg.get("output", {}).get("dir", "site"), "data", "profile.json")
    if not os.path.isfile(out):
        return {}
    try:
        with open(out, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return {}


def is_junk(title: str) -> bool:
    return bool(JUNK.search(title or ""))


def prepare_pool(config: dict, quiet: bool = False) -> tuple[dict[str, list[Article]], list, bool]:
    proxy = detect_proxy()
    set_proxy(proxy)
    # 云端 runner 本身就在墙外，没有代理也能抓国际源
    allow_intl = proxy is not None or bool(os.environ.get("CI"))
    log(f"网络：{'经代理 ' + proxy if proxy else '直连（跳过需要代理的国际源）'}", quiet)

    articles, sources = fetch_all(config, allow_intl)
    ok = sum(1 for s in sources if s.ok)
    log(f"抓取：{ok}/{len(sources)} 源正常，{len(articles)} 篇", quiet)

    profile = load_profile(config)
    sec_weight = profile.get("section_weight") or {}
    kw_boost = [str(k) for k in (profile.get("keyword_boost") or []) if k]

    articles = [a for a in articles if not is_junk(a.title)]
    articles = cluster.dedupe_by_url(articles)
    by_section: dict[str, list[Article]] = {}
    for sec in config["sections"]:
        pool = cluster.cluster([a for a in articles if a.section == sec["key"]])
        factor = float(sec_weight.get(sec["key"], 1.0))
        for a in pool:
            a.weight *= factor
            if any(k in (a.title + a.excerpt) for k in kw_boost):
                a.weight *= 1.25
        by_section[sec["key"]] = rank.rank(pool, sec.get("keywords", []))
    return by_section, sources, allow_intl


def fallback_picks(config: dict, pool: dict[str, list[Article]]) -> list[dict]:
    quota = config.get("selection", {}).get("quota", {})
    picks = []
    for sec in config["sections"]:
        n = int(quota.get(sec["key"], 2))
        for art in pool.get(sec["key"], [])[:n]:
            picks.append({"article": art, "section": sec["key"], "importance": 2 if n <= 2 else 1})
    return picks


def ensure_coverage(picks: list[dict], cfg: dict, pool: dict[str, list[Article]]) -> list[dict]:
    """保证七个栏目都有内容，再按重要性裁到上限。"""
    have = {p["section"] for p in picks}
    used = {p["article"].url for p in picks}
    for sec in cfg["sections"]:
        if sec["key"] in have:
            continue
        cand = [a for a in pool.get(sec["key"], []) if a.url not in used]
        if cand:
            picks.append({"article": cand[0], "section": sec["key"], "importance": 2})
            used.add(cand[0].url)
    cap = int(cfg.get("max_items", 18))
    if len(picks) <= cap:
        return picks
    # 先按重要性升序尝试剔除，但每个栏目至少留一条
    order = {s["key"]: i for i, s in enumerate(cfg["sections"])}
    picks.sort(key=lambda p: (int(p["importance"]), -order.get(p["section"], 9)))
    keep: list[dict] = []
    seen: set[str] = set()
    for p in picks:
        if p["section"] in seen:
            continue
        keep.append(p)
        seen.add(p["section"])
    rest = [p for p in picks if p not in keep]
    rest.sort(key=lambda p: -int(p["importance"]))
    for p in rest:
        if len(keep) >= cap:
            break
        keep.append(p)
    keep.sort(key=lambda p: (-int(p["importance"]), order.get(p["section"], 9)))
    return keep


def fetch_bodies(arts: list[Article], quiet: bool = False) -> None:
    def work(a: Article) -> None:
        if a.url:
            a.body, a.html = fetch_article(a.url)

    log(f"抓正文 {len(arts)} 篇…", quiet)
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(work, arts))
    ok = sum(1 for a in arts if len(a.body) > 200)
    log(f"正文成功 {ok}/{len(arts)}", quiet)


def attach_images(items: list[dict], art_map: dict, cfg: dict, quiet: bool = False) -> None:
    """为重要条目配一张报道方原图；找不到就不配，绝不用占位图。"""
    conf = cfg.get("images") or {}
    if not conf.get("enabled", True):
        return
    limit = int(conf.get("max_items", 14))
    todo = [it for it in items[:limit] if it.get("url") in art_map and art_map[it["url"]].html]
    log(f"配图 {len(todo)} 条…", quiet)

    def work(it: dict):
        art = art_map[it["url"]]
        try:
            pics = media.pick(art.html, art.url, limit=1)
        except Exception:  # noqa: BLE001
            return it, None
        return it, (pics[0] if pics else None)

    results = []
    with cf.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(work, todo))

    # 串行分配并去重：并发里判断 used 会漏掉同一张图
    used: set[str] = set()
    for it, pic in results:
        if not pic or pic.url in used:
            continue
        used.add(pic.url)
        it["image"] = {
            "url": pic.url,
            "w": pic.width,
            "h": pic.height,
            "alt": pic.alt,
            "credit": f"图片来源：{art_map[it['url']].source}",
        }
    with_img = sum(1 for it in items if it.get("image"))
    log(f"  成功配图 {with_img} 条", quiet)


def build_issue(cfg: dict, *, no_llm: bool = False, quiet: bool = False) -> dict:
    started = time.time()
    now = datetime.now(TZ)
    log(f"周报 v2 · {week_label(now)} · {week_range(now)}", quiet)

    pool, sources, allow_intl = prepare_pool(cfg, quiet)
    llm_cfg = cfg.get("llm", {})
    use_llm = bool(llm_cfg.get("enabled", True)) and not no_llm and bool(
        os.environ.get(llm_cfg.get("api_key_env", "DEEPSEEK_API_KEY"), "").strip()
    )
    if not use_llm:
        log("未启用模型：走规则版", quiet)

    picks: list[dict] = []
    opening, note = "", ""
    if use_llm:
        log("模型精选…", quiet)
        picks, note = summarize.curate(cfg["sections"], pool, llm_cfg)
        log(f"  选中 {len(picks)} 条", quiet)
    if not picks:
        picks = fallback_picks(cfg, pool)
        log(f"  本地兜底选中 {len(picks)} 条", quiet)

    picks = ensure_coverage(picks, cfg, pool)
    arts = [p["article"] for p in picks]
    fetch_bodies(arts, quiet)

    by_sec: dict[str, list[Article]] = {}
    for p in picks:
        by_sec.setdefault(p["section"], []).append(p["article"])

    contents: dict[str, dict] = {}
    if use_llm:
        log("写摘要…", quiet)
        for sec in cfg["sections"]:
            group = by_sec.get(sec["key"]) or []
            if not group:
                continue
            got = summarize.write_items(sec, group, llm_cfg)
            contents.update(got)
            log(f"  {sec['name']}：{len(got)}/{len(group)}", quiet)

    # 排序：重要性优先，其次栏目权重
    order = {s["key"]: i for i, s in enumerate(cfg["sections"])}
    picks.sort(key=lambda p: (-int(p["importance"]), order.get(p["section"], 9)))

    items: list[dict] = []
    for p in picks:
        art: Article = p["article"]
        content = contents.get(art.url) or (summarize.rule_content(art) if not use_llm else summarize.rule_content(art))
        item = {
            "id": art.id,
            "section": p["section"],
            "importance": int(p["importance"]),
            "headline": str(content.get("headline") or art.title)[:40],
            "summary": (
                ("（英文原文，未翻译）" if art.lang == "en" and not use_llm else "")
                + str(content.get("summary") or "")
            )[:230],
            "why": str(content.get("why") or "")[:80],
            "keywords": [str(k)[:12] for k in (content.get("keywords") or [])][:5],
            "event_date": str(content.get("event_date") or "")[:12],
            "take": {"mode": "short", "text": str(content.get("take") or "")[:200]},
            "url": art.url,
            "source": art.source,
            "sources_all": sorted({art.source, *art.duplicates}),
            "date_pub": art.published.strftime("%m/%d") if art.published else "",
            "lang": art.lang,
        }
        items.append(item)

    # 深度评论：前 4 条重要新闻
    if use_llm and items:
        top = [it for it in items if it["importance"] >= 2][:4]
        if top:
            art_map = {a.url: a for a in arts}
            log(f"写深度评论 {len(top)} 条…", quiet)
            deep = summarize.write_commentaries(
                [art_map[it["url"]] for it in top if it["url"] in art_map],
                {it["url"]: it["summary"] for it in top},
                llm_cfg,
            )
            for it in top:
                d = deep.get(it["url"])
                if d and d.get("background"):
                    it["take"] = {
                        "mode": "full",
                        "background": str(d.get("background", "")),
                        "impact": str(d.get("impact", "")),
                        "perspectives": str(d.get("perspectives", "")),
                        "questions": [str(q) for q in (d.get("questions") or [])][:2],
                    }

    sections_out = []
    for sec in cfg["sections"]:
        group = [it for it in items if it["section"] == sec["key"]]
        if not group:
            continue
        sections_out.append(
            {
                "key": sec["key"],
                "idx": sec.get("idx", ""),
                "name": sec["name"],
                "en": sec.get("en", ""),
                "blurb": sec["blurb"],
                "accent": sec["accent"],
                "items": group,
            }
        )

    attach_images(items, {a.url: a for a in arts}, cfg, quiet)

    if use_llm:
        log("写开场白与深度观察…", quiet)
        lines = [f"- {s['name']}：{s['items'][0]['headline']}" for s in sections_out]
        meta = summarize.write_opening(lines, llm_cfg)
        opening = meta.get("opening", "") or opening
        note = note or meta.get("note", "")
        dd = summarize.write_deep_dive(items, llm_cfg)
    else:
        dd = {"deep_dive": {}, "questions3": []}

    watch = [str(w) for w in (load_profile(cfg).get("watch") or [])]
    if watch:
        for it in items:
            text = it["headline"] + it["summary"] + " ".join(it["keywords"])
            hits = [w for w in watch if w and w[:8] in text]
            if hits:
                it["watch"] = hits[:2]

    top_ids = [it["id"] for it in items[:5]]
    issue = {
        "edition": 2,
        "week": week_label(now),
        "range": week_range(now),
        "generated_at": now.isoformat(timespec="minutes"),
        "generated_date": fmt_cn(now),
        "opening": opening,
        "note": note,
        "mode": "llm" if use_llm else "rule",
        "top_ids": top_ids,
        "sections": sections_out,
        "deep_dive": dd.get("deep_dive") or {},
        "questions3": dd.get("questions3") or [],
        "sources": [
            {"name": s.name, "section": s.section, "ok": s.ok, "count": s.count, "error": s.error}
            for s in sources
        ],
        "stats": {
            "articles": sum(len(v) for v in pool.values()),
            "sources_total": len(sources),
            "sources_ok": sum(1 for s in sources if s.ok),
            "items": len(items),
            "elapsed": round(time.time() - started, 1),
            "usage": usage_summary(),
            "intl": allow_intl,
        },
    }
    log(f"完成：{len(items)} 条，{issue['stats']['elapsed']}s", quiet)
    return issue


def save_issue(issue: dict, cfg: dict) -> str:
    out_dir = os.path.join(ROOT, cfg.get("output", {}).get("dir", "site"))
    data_dir = os.path.join(out_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, f"{issue['week']}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(issue, fh, ensure_ascii=False, indent=1)
    return path


def build_search_index(cfg: dict) -> str:
    """汇总所有期数的条目，供历史检索页使用。"""
    out_dir = os.path.join(ROOT, cfg.get("output", {}).get("dir", "site"))
    data_dir = os.path.join(out_dir, "data")
    records = []
    issues = []
    if os.path.isdir(data_dir):
        for name in sorted(os.listdir(data_dir), reverse=True):
            if not name.endswith(".json") or name in ("index.json", "profile.json"):
                continue
            try:
                with open(os.path.join(data_dir, name), encoding="utf-8") as fh:
                    d = json.load(fh)
            except Exception:  # noqa: BLE001
                continue
            issues.append(
                {
                    "week": d.get("week", name[:-5]),
                    "range": d.get("range", ""),
                    "note": d.get("note", ""),
                    "items": sum(len(s["items"]) for s in d.get("sections", [])),
                }
            )
            for sec in d.get("sections", []):
                for it in sec["items"]:
                    records.append(
                        {
                            "w": d.get("week", ""),
                            "s": sec.get("name", ""),
                            "h": it.get("headline", ""),
                            "d": (it.get("summary") or "")[:120],
                            "u": it.get("url", ""),
                            "k": " ".join(it.get("keywords") or []),
                            "i": it.get("id", ""),
                        }
                    )
    path = os.path.join(data_dir, "index.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"issues": issues, "items": records}, fh, ensure_ascii=False)
    return path


if __name__ == "__main__":
    raise SystemExit("请用 run.py 运行")
