"""按兴趣相关度打分排序：来源权重、跨源覆盖、新鲜度、关键词命中。"""
from __future__ import annotations

import math
import re
import time

from .cluster import story_count
from .fetch import Article
from .util import normalize_for_match


# 低价值内容：促销、导购、教程、花边
LOW_VALUE = re.compile(
    r"(直降|降价|优惠|促销|特价|白菜|好价|双十一|双11|补贴|立省|到手价|秒杀|折扣|开箱|图赏|壁纸|"
    r"教程|技巧|攻略|怎么|如何|盘点|推荐|选购|值不值得|该买|买哪|早报|晚报|日报|午报|周报|"
    r"今日要闻|快讯汇总|newsletter|deal|discount|sale\b|promo|"
    r"how to|tips|tutorial|guide|best |roundup|deals|gift)",
    re.I,
)
# 高价值内容：发布、融资、收购、召回、技术突破
HIGH_VALUE = re.compile(
    r"(发布|官宣|亮相|首发|上市|开售|迭代|升级|融资|收购|并购|裁员|合作|召回|曝光|泄漏|泄露|"
    r"突破|首款|全球首|量产|交付|获批|起诉|禁令|"
    r"launch|unveil|announce|raise|acquire|reveal|recall|leak|debut|first look|sue|ban)",
    re.I,
)


def quality_delta(title: str) -> float:
    delta = 0.0
    if LOW_VALUE.search(title):
        delta -= 0.55
    if HIGH_VALUE.search(title):
        delta += 0.3
    return delta


def score(
    art: Article,
    keywords: list[str],
    now: float | None = None,
    zh_boost: float = 0.0,
) -> float:
    now = now or time.time()
    value = art.weight
    value += 0.38 * (story_count(art) - 1)  # 多个源都在报，说明重要
    if art.published:
        age_h = max(0.0, (now - art.published.timestamp()) / 3600)
        value += max(0.0, 1.0 - age_h / 72)  # 72 小时内线性衰减
    value += quality_delta(art.title)
    if zh_boost and art.lang == "zh":
        value += zh_boost  # 没有翻译时，优先给能直接读的中文内容
    haystack = normalize_for_match(art.title + " " + art.excerpt[:300])
    if keywords:
        hits = sum(1 for kw in keywords if normalize_for_match(kw) and normalize_for_match(kw) in haystack)
        value += min(0.6, 0.12 * hits)
    if len(art.excerpt) < 20 and not art.body:
        value -= 0.3  # 几乎没内容的条目降权
    return value


def rank(
    articles: list[Article],
    keywords: list[str],
    limit: int | None = None,
    zh_boost: float = 0.0,
) -> list[Article]:
    now = time.time()
    scored = sorted(articles, key=lambda a: score(a, keywords, now, zh_boost), reverse=True)
    return scored[:limit] if limit else scored


def pick(
    articles: list[Article],
    detailed: int,
    brief: int,
    keywords: list[str],
    cap: int | None = None,
    zh_boost: float = 0.0,
) -> tuple[list[Article], list[Article]]:
    return pick_ranked(rank(articles, keywords, zh_boost=zh_boost), detailed, brief, cap)


def pick_ranked(
    ranked: list[Article],
    detailed: int,
    brief: int,
    cap: int | None = None,
    detailed_cap: int = 2,
) -> tuple[list[Article], list[Article]]:
    """从已排序的列表里挑条目，同时限制单一来源的占比，避免整期被一家媒体刷屏。"""
    need = detailed + brief
    n_sources = len({a.source for a in ranked}) or 1
    cap = cap or max(3, math.ceil(need / n_sources))
    deep: list[Article] = []
    quick: list[Article] = []
    counts: dict[str, int] = {}
    deep_counts: dict[str, int] = {}
    used: set[str] = set()

    def take(limit_deep: int) -> None:
        for art in ranked:
            if art.url in used:
                continue
            if len(deep) >= detailed and len(quick) >= brief:
                return
            if counts.get(art.source, 0) >= cap:
                continue
            if len(deep) < detailed:
                if deep_counts.get(art.source, 0) >= limit_deep:
                    continue
                deep.append(art)
                deep_counts[art.source] = deep_counts.get(art.source, 0) + 1
            elif len(quick) < brief:
                quick.append(art)
            else:
                return
            counts[art.source] = counts.get(art.source, 0) + 1
            used.add(art.url)

    take(detailed_cap)
    if len(deep) < detailed:  # 源太少时放宽限制，保证详读条数
        take(detailed)
    return deep, quick
