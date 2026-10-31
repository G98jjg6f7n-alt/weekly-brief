"""主流程：抓取 → 路由 → 去重聚类 → 排序 → 抓正文 → 摘要 → 渲染 → 归档。"""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import sys
import time
from datetime import datetime

from . import cluster, rank
from .extract import fetch_body
from .fetch import Article, fetch_all
from .summarize import SectionDigest, find_duplicate_groups, summarize_section, usage_summary, write_opening
from .util import fmt_cn, normalize_for_match, TZ, week_label, week_range

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config(path: str | None = None) -> dict:
    path = path or os.path.join(ROOT, "config.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def log(msg: str, quiet: bool = False) -> None:
    if not quiet:
        print(msg, flush=True)


def route_articles(articles: list[Article], sections: list[dict]) -> list[Article]:
    """把综合源（IT之家、爱范儿等）里的汽车/摄影文章分流到对应板块。

    打分规则：标题命中算 2 分、摘要命中算 1 分，总分 >= 2 才搬走；
    标题里出现该板块的排除词（比如摄影板块的「电影」「游戏」）直接不搬。
    综合源文章量大，这一步宁严勿滥，否则《沙丘 3》预告会跑进摄影板块。
    """
    kw = {
        s["key"]: [k for k in (s.get("route_keywords") or s.get("keywords", [])) if k]
        for s in sections
    }
    exclude = {s["key"]: (s.get("route_exclude") or []) for s in sections}
    # route 是写在「源」上的：这些综合源的文章按关键词重新归到更合适的板块
    routable = {
        src["name"]
        for sec in sections
        for src in sec.get("sources", [])
        if src.get("route")
    }
    for art in articles:
        if art.source not in routable:
            continue
        title = normalize_for_match(art.title)
        body = normalize_for_match(art.excerpt[:400])
        if not title and not body:
            continue
        scores: dict[str, int] = {}
        for key, words in kw.items():
            score = 0
            for w in words:
                nw = normalize_for_match(w)
                if not nw:
                    continue
                if nw in title:
                    score += 2
                elif nw in body:
                    score += 1
            if score:
                scores[key] = score
        if not scores:
            continue
        best = max(scores, key=scores.get)
        if best == art.section or scores[best] < 2:
            continue
        if scores[best] <= scores.get(art.section, 0):
            continue
        if any(ex in art.title for ex in exclude.get(best, [])):
            continue
        art.section = best
    return articles


def fetch_bodies(articles: list[Article], workers: int = 8, quiet: bool = False) -> None:
    def work(art: Article) -> None:
        if art.url:
            art.body = fetch_body(art.url)

    todo = [a for a in articles if a.url]
    log(f"  抓正文 {len(todo)} 篇…", quiet)
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(work, todo))
    ok = sum(1 for a in todo if len(a.body) > 200)
    log(f"  正文成功 {ok}/{len(todo)}", quiet)


def build_issue(cfg: dict, *, no_llm: bool = False, only: list[str] | None = None, quiet: bool = False) -> dict:
    started = time.time()
    now = datetime.now(TZ)
    log(f"周报生成 · {week_label(now)} · {week_range(now)}", quiet)

    log("1/6 抓取订阅源…", quiet)
    articles, sources = fetch_all(cfg)
    ok_sources = [s for s in sources if s.ok]
    log(f"  {len(ok_sources)}/{len(sources)} 个源正常，{len(articles)} 篇文章", quiet)

    log("2/6 分流与去重…", quiet)
    articles = route_articles(articles, cfg["sections"])
    articles = cluster.dedupe_by_url(articles)

    per = cfg.get("per_section", {"detailed": 3, "brief": 7})
    llm_cfg = cfg.get("llm", {})
    use_llm = bool(llm_cfg.get("enabled", True)) and not no_llm and bool(
        os.environ.get(llm_cfg.get("api_key_env", "DEEPSEEK_API_KEY"), "").strip()
    )
    # 大模型不可用时没有翻译，优先把能直接读的中文内容排上来
    zh_boost = 0.0 if use_llm else float(cfg.get("rule_mode_zh_boost", 0.5))
    ranked: dict[str, list[Article]] = {}
    for sec in cfg["sections"]:
        if only and sec["key"] not in only:
            continue
        pool = [a for a in articles if a.section == sec["key"]]
        clustered = cluster.cluster(pool)
        ranked[sec["key"]] = rank.rank(clustered, sec.get("keywords", []), zh_boost=zh_boost)
        log(f"  {sec['cn']:<4} 候选 {len(pool):>3d} → 聚类 {len(clustered):>3d}", quiet)

    if use_llm:
        log("  跨板块查重（同一事件只留一条）…", quiet)
        listing = [
            {"section": sec["cn"], "title": art.title}
            for sec in cfg["sections"] if sec["key"] in ranked
            for art in ranked[sec["key"]][:24]
        ]
        groups = find_duplicate_groups(listing, llm_cfg)
        drop: set[str] = set()
        for group in groups:
            for idx in group[1:]:
                drop.add(listing[idx - 1]["title"])
        if drop:
            for key in ranked:
                ranked[key] = [a for a in ranked[key] if a.title not in drop]
            log(f"  合并 {sum(len(g) - 1 for g in groups)} 条重复报道（{len(groups)} 组）", quiet)

    picked: dict[str, tuple[list[Article], list[Article]]] = {}
    for sec in cfg["sections"]:
        if sec["key"] not in ranked:
            continue
        detailed, brief = rank.pick_ranked(ranked[sec["key"]], int(per["detailed"]), int(per["brief"]))
        picked[sec["key"]] = (detailed, brief)
        log(f"  {sec['cn']:<4} 详读 {len(detailed)} + 速览 {len(brief)}", quiet)

    log("3/6 抓取正文…", quiet)
    selected = [a for pair in picked.values() for group in pair for a in group]
    fetch_bodies(selected, quiet=quiet)

    log("4/6 生成摘要…", quiet)
    if no_llm:
        log("  --no-llm：强制使用规则摘要", quiet)
    elif not use_llm:
        log("  未检测到 API Key：使用规则摘要（配置 Key 后可自动升级为双语摘要）", quiet)

    digests: list[SectionDigest] = []
    for sec in cfg["sections"]:
        if sec["key"] not in picked:
            continue
        detailed, brief = picked[sec["key"]]
        if use_llm:
            digest = summarize_section(sec, detailed, brief, llm_cfg)
        else:
            digest = SectionDigest(
                key=sec["key"], name=sec["name"], cn=sec.get("cn", ""),
                blurb=sec.get("blurb", ""), accent=sec.get("accent", "#333"),
            )
            from .summarize import _rule_fill

            _rule_fill(digest, detailed, brief)
            digest.intro = f"本周{sec.get('cn', sec['name'])}领域共 {len(digest.items)} 条更新。"
        digests.append(digest)
        log(f"  {sec['cn']:<4} 摘要 {len(digest.items)} 条{'（规则）' if digest.note else ''}", quiet)

    failed = [d for d in digests if d.note]
    opening = ""
    if use_llm and digests and len(failed) < len(digests):
        log("5/6 生成开场白…", quiet)
        opening = write_opening(digests, llm_cfg)
    if failed:
        log(f"  注意：{len(failed)} 个板块降级为规则摘要", quiet)
    mode = "rule" if not use_llm or len(failed) == len(digests) else ("mixed" if failed else "llm")

    issue = {
        "week": week_label(now),
        "range": week_range(now),
        "generated_at": now.isoformat(timespec="minutes"),
        "generated_date": fmt_cn(now),
        "opening": opening,
        "mode": mode,
        "sections": [_digest_to_dict(d) for d in digests],
        "sources": [
            {"name": s.name, "section": s.section, "ok": s.ok, "count": s.count, "error": s.error}
            for s in sources
        ],
        "stats": {
            "articles": len(articles),
            "sources_total": len(sources),
            "sources_ok": len(ok_sources),
            "elapsed": round(time.time() - started, 1),
            "usage": usage_summary(),
        },
    }
    log(f"完成，用时 {issue['stats']['elapsed']}s", quiet)
    return issue


def _digest_to_dict(d: SectionDigest) -> dict:
    return {
        "key": d.key,
        "name": d.name,
        "cn": d.cn,
        "blurb": d.blurb,
        "accent": d.accent,
        "intro": d.intro,
        "note": d.note,
        "items": [
            {
                "headline": it.headline,
                "points": [{"en": p.en, "zh": p.zh} for p in it.points],
                "why": it.why,
                "url": it.url,
                "source": it.source,
                "sources_all": it.sources_all,
                "date": it.published.strftime("%m/%d") if it.published else "",
                "lang": it.lang,
                "detailed": it.detailed,
            }
            for it in (d.detailed + d.brief)
        ],
    }


def save_issue(issue: dict, cfg: dict, preview: bool = False) -> str:
    out_dir = os.path.join(ROOT, cfg.get("output", {}).get("dir", "site"))
    data_dir = os.path.join(out_dir, "preview" if preview else "data")
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, f"{issue['week']}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(issue, fh, ensure_ascii=False, indent=1)
    return path


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    no_llm = "--no-llm" in argv
    only = None
    for i, arg in enumerate(argv):
        if arg == "--only" and i + 1 < len(argv):
            only = argv[i + 1].split(",")
    cfg = load_config()
    issue = build_issue(cfg, no_llm=no_llm, only=only)

    from .render import render_issue, write_site

    html = render_issue(issue, cfg)
    path = write_site(issue, html, cfg)
    save_issue(issue, cfg)
    print(f"已生成：{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
