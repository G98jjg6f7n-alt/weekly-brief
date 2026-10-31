"""跨源去重与聚类：同一件事只保留一条，其余记为来源。"""
from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

from .fetch import Article
from .util import jaccard, shingles

TRACKING = re.compile(r"(utm_[a-z]+|spm|from|ref|share_source|s_cid|fbclid)=[^&]*")


def canonical_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        query = TRACKING.sub("", parts.query).strip("&")
        path = parts.path.rstrip("/")
        return urlunsplit((parts.scheme, parts.netloc.lower().replace("www.", ""), path, query, ""))
    except Exception:  # noqa: BLE001
        return url


def dedupe_by_url(articles: list[Article]) -> list[Article]:
    seen: dict[str, Article] = {}
    for art in articles:
        key = canonical_url(art.url)
        if key in seen:
            seen[key].duplicates.append(art.source)
            continue
        seen[key] = art
    return list(seen.values())


def cluster(articles: list[Article], threshold: float = 0.46) -> list[Article]:
    """标题相似度聚类，返回每个故事的代表条目（保留来源最多、权重最高的那条）。"""
    ordered = sorted(articles, key=lambda a: (a.weight, bool(a.published)), reverse=True)
    clusters: list[tuple[set[str], Article]] = []
    for art in ordered:
        title_sh = shingles(art.title, 3)
        hit = None
        for existing, rep in clusters:
            score = jaccard(title_sh, existing)
            if score >= threshold:
                hit = rep
                break
        if hit is not None:
            hit.duplicates.append(art.source)
            if art.published and (not hit.published or art.published < hit.published):
                hit.published = art.published
            continue
        clusters.append((title_sh, art))
    return [rep for _, rep in clusters]


def story_count(art: Article) -> int:
    return 1 + len(set(art.duplicates))
