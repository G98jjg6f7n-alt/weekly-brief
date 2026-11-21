"""主流程 v2：抓取 → 预筛 → 模型精选 → 正文 → 卡片与评论 → 深度观察 → 渲染。"""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import re
import time
from datetime import datetime

from . import cluster, rank, summarize
from .extract import fetch_article
from .fetch import Article, detect_proxy, fetch_all, set_proxy
from .llm import usage_summary
from .util import TZ, fmt_cn, week_label, week_range

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

JUNK = re.compile(
    r"(明星|绯闻|八卦|恋情|官宣恋情|结婚|离婚|婚纱|写真|整容|网红|带货|彩票|中奖|双色球|"
    r"开奖|运势|星座|风水|算命|灵异|猎奇|视频欣赏|组图|图集)"
)

# 地方性、仪式性、事务性报道：只有同时缺少高信号词时才丢弃
NOISE = re.compile(
    r"(走访|慰问|调研|座谈|揭牌|启动仪式|表彰|荣获|获评|喜讯|茶话会|观摩|督查|视察|"
    r"签约仪式|奠基|竣工|开学典礼|毕业典礼|欢送|欢迎仪式|周年庆|店庆|抽奖|"
    r"侧记|见闻|特写|直击|花絮|盘点|一览)"
)
SIGNAL = re.compile(
    r"(政策|法案|条例|预算|数据|报告|研究|发现|突破|发布|全国|全球|亿元|万人|"
    r"立法|判决|禁令|调查|危机|增长|下降|失业|通胀|关税|协议|选举|战争)"
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
    t = title or ""
    if JUNK.search(t):
        return True
    if len(t.strip()) < 8:
        return True
    if NOISE.search(t) and not SIGNAL.search(t):
        return True
    return False


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


def _cn_headline(headline: str, lede: str) -> str:
    """标题必须是中文；模型漏译时退回导语；都还是英文就丢稿。"""
    if re.search(r"[\u4e00-\u9fff]", headline):
        return headline[:40]
    fallback = (lede or headline).strip()
    if re.search(r"[\u4e00-\u9fff]", fallback):
        return fallback[:40]
    return ""


INTERP = re.compile(r"(解析|解读|分析|评论|调查|幕后|为何|如何|深度|专访|复盘|观点|社论)")


def _bgset(text: str) -> set[str]:
    t = "".join(ch for ch in (text or "") if ch.strip())
    return {t[i:i + 2] for i in range(max(0, len(t) - 1))}


def _editor_dedupe(picks: list[dict], llm_cfg: dict, quiet: bool) -> list[dict]:
    """让模型做编辑查重：同一件事只留一条。失败则原样返回。"""
    if len(picks) < 2:
        return picks
    titles = [p["article"].title for p in picks]
    try:
        drop = summarize.dedupe(titles, llm_cfg)
    except Exception:  # noqa: BLE001
        return picks
    drop = [i for i in set(drop) if 0 <= i < len(picks)]
    if not drop or len(drop) > len(picks) // 3:
        return picks
    log(f"  编辑查重去掉 {len(drop)} 条同事件报道", quiet)
    return [p for i, p in enumerate(picks) if i not in set(drop)]


def _drop_repeat_headlines(items: list[dict]) -> list[dict]:
    """模型写出来的标题再查一遍重：同一件事只留分数最高的一条（另有一篇不同角度的分析除外）。"""
    kept: list[dict] = []
    counted: dict[int, int] = {}
    for it in sorted(items, key=lambda x: (-float(x.get("score", 0)), -int(x.get("importance", 0)))):
        A = _bgset(it["headline"])
        dup = False
        for i, k in enumerate(kept):
            B = _bgset(k["headline"])
            if not A or not B:
                continue
            close = len(A & B) / max(1, min(len(A), len(B))) > 0.42
            same_prefix = k["source"] == it["source"] and it["headline"][:5] == k["headline"][:5]
            if close or same_prefix:
                interp = bool(INTERP.search(it["headline"]))
                if k["source"] == it["source"] or not interp or counted.get(i, 1) >= 2:
                    dup = True
                    break
                counted[i] = counted.get(i, 1) + 1
                break
        if not dup:
            kept.append(it)
    return kept


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
        want_min = int(cfg.get("min_items", 12)) + 2
        picks = _editor_dedupe(picks, llm_cfg, quiet)
        if len(picks) < want_min:
            need = want_min - len(picks)
            log(f"  首轮 {len(picks)} 条偏少，补选 {need} 条…", quiet)
            have_sec = {p["section"] for p in picks}
            more, _ = summarize.curate(
                cfg["sections"], pool, llm_cfg,
                exclude={p["article"].url for p in picks},
                floor=6.0, want=need + 3,
                bias=[s["key"] for s in cfg["sections"] if s["key"] not in have_sec],
            )
            have = {p["article"].url for p in picks}
            picks.extend(m for m in more if m["article"].url not in have)
            picks = _editor_dedupe(picks, llm_cfg, quiet)
        log(f"  选中 {len(picks)} 条", quiet)
    if not picks:
        picks = fallback_picks(cfg, pool)
        log(f"  本地兜底选中 {len(picks)} 条", quiet)

    if not use_llm:
        picks = ensure_coverage(picks, cfg, pool)
    arts = [p["article"] for p in picks]
    fetch_bodies(arts, quiet)

    by_sec: dict[str, list[Article]] = {}
    for p in picks:
        by_sec.setdefault(p["section"], []).append(p["article"])

    max_major = int((cfg.get("selection") or {}).get("max_major", 5))
    ranked = sorted(picks, key=lambda p: (-float(p.get("score", 5)), -int(p["importance"])))
    tiers: dict[str, str] = {}
    per_sec_major: dict[str, int] = {}
    used_major = 0
    for p in ranked:
        sec_key = p["section"]
        can = (
            used_major < max_major
            and int(p["importance"]) >= 2
            and per_sec_major.get(sec_key, 0) < 2
        )
        tiers[p["article"].url] = "major" if can else "brief"
        if can:
            used_major += 1
            per_sec_major[sec_key] = per_sec_major.get(sec_key, 0) + 1

    contents: dict[str, dict] = {}
    if use_llm:
        log("撰写报道…", quiet)
        for sec in cfg["sections"]:
            group = by_sec.get(sec["key"]) or []
            if not group:
                continue
            got = summarize.write_items(sec, group, llm_cfg, tiers=tiers)
            contents.update(got)
            nmajor = sum(1 for a in group if tiers.get(a.url) == "major")
            log(f"  {sec['name']}：{len(got)}/{len(group)}（深 {nmajor}）", quiet)

    # 排序：重要性优先，其次栏目权重
    order = {s["key"]: i for i, s in enumerate(cfg["sections"])}
    picks.sort(key=lambda p: (-int(p["importance"]), order.get(p["section"], 9)))

    items: list[dict] = []
    for p in picks:
        art: Article = p["article"]
        content = contents.get(art.url) or (summarize.rule_content(art) if not use_llm else summarize.rule_content(art))
        blocks = [b for b in (content.get("blocks") or []) if b.get("p")]
        if not blocks:
            paras = [str(x) for x in (content.get("paras") or []) if str(x).strip()]
            blocks = [{"h": "", "p": x} for x in paras]
        if not blocks:
            blocks = [{"h": "", "p": str(art.excerpt or art.title or "")}]
        # 只对短稿去掉与导语重复的首段；重点报道必须保留「发生了什么」
        lede0 = str(content.get("lede") or "")
        if lede0 and blocks and str(content.get("tier")) != "major":
            ov = len(set(lede0) & set(blocks[0]["p"])) / max(1, len(set(lede0)))
            if ov > 0.72 and len(blocks) > 1:
                blocks = blocks[1:]
        text_all = " ".join(b["p"] for b in blocks)
        item = {
            "id": art.id,
            "section": p["section"],
            "importance": int(p["importance"]),
            "tier": str(content.get("tier") or tiers.get(art.url) or "brief"),
            "score": float(p.get("score", 0) or 0),
            "why": str(p.get("why") or ""),
            "headline": _cn_headline(str(content.get("headline") or art.title), str(content.get("lede") or "")),
            "lede": str(content.get("lede") or ""),
            "blocks": blocks,
            "summary": str(content.get("lede") or "") + " " + text_all,
            "keywords": [str(k)[:12] for k in (content.get("keywords") or [])][:4],
            "url": art.url,
            "source": art.source,
            "sources_all": sorted({art.source, *art.duplicates}),
            "date_pub": art.published.strftime("%m/%d") if art.published else "",
            "lang": art.lang,
        }
        if not item["headline"]:
            continue
        items.append(item)

    items = _drop_repeat_headlines(items)

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
