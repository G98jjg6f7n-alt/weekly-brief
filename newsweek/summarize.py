"""摘要引擎：大模型优先，规则兜底。任何时候都要产出内容。"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime

from .fetch import Article
from .util import normalize_for_match, split_sentences, truncate


@dataclass
class Point:
    en: str = ""
    zh: str = ""


@dataclass
class Item:
    headline: str
    points: list[Point] = field(default_factory=list)
    why: str = ""
    url: str = ""
    source: str = ""
    published: datetime | None = None
    lang: str = "zh"
    detailed: bool = False
    sources_all: list[str] = field(default_factory=list)


@dataclass
class SectionDigest:
    key: str
    name: str
    cn: str
    blurb: str
    accent: str
    intro: str = ""
    items: list[Item] = field(default_factory=list)
    detailed: list[Item] = field(default_factory=list)
    brief: list[Item] = field(default_factory=list)
    note: str = ""


class LLMError(RuntimeError):
    pass


USAGE = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}


def usage_summary() -> dict:
    return dict(USAGE)


SYSTEM_PROMPT = """你是一位资深中文科技媒体编辑，为一位中国大学生撰写每周新闻周报。
你的读者对 AI、汽车、数码、摄影感兴趣，正在学英语。
你必须只输出一个 JSON 对象，不要输出任何解释、前后缀或 Markdown 代码块。"""

SCHEMA_HINT = """输出 JSON 结构：
{
  "intro": "本板块 2 句话导语，概括本周这一领域的整体动向，不要罗列条目",
  "items": [
    {
      "n": 原始编号(整数),
      "headline_zh": "不超过 22 字的中文小标题，要有信息量，不要写成标题党",
      "points": [{"en": "英文原句", "zh": "中文翻译"}],
      "why": "一句话说明为什么值得关注，不超过 30 字"
    }
  ]
}"""


def _post_json(url: str, payload: dict, api_key: str, timeout: int) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def call_llm(cfg: dict, system: str, user: str, max_tokens: int | None = None) -> str:
    api_key = os.environ.get(cfg.get("api_key_env", "DEEPSEEK_API_KEY"), "").strip()
    if not api_key:
        raise LLMError("no api key")
    base = (
        os.environ.get("DEEPSEEK_BASE_URL") or cfg.get("base_url", "https://api.deepseek.com")
    ).rstrip("/")
    payload = {
        "model": os.environ.get("DEEPSEEK_MODEL") or cfg.get("model", "deepseek-flash"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": cfg.get("temperature", 0.3),
        "max_tokens": max_tokens or cfg.get("max_tokens", 4000),
        "response_format": {"type": "json_object"},
        "stream": False,
    }
    # DeepSeek 的思考模式默认开启，会拖慢速度、抬高价格，而且思维链会混进 JSON；
    # 这里显式关掉。换用不认识该字段的兼容接口时，下面会自动去掉它重试一次。
    extra = dict(cfg.get("extra_body") or {})
    payload.update(extra)
    last: Exception | None = None
    deadline = time.time() + float(cfg.get("deadline_seconds", 600))
    max_attempts = 3
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        if time.time() > deadline:
            raise LLMError(f"超时放弃：{last}")
        try:
            body = _post_json(f"{base}/chat/completions", payload, api_key, cfg.get("timeout", 120))
            usage = body.get("usage") or {}
            USAGE["prompt_tokens"] += int(usage.get("prompt_tokens", 0))
            USAGE["completion_tokens"] += int(usage.get("completion_tokens", 0))
            USAGE["calls"] += 1
            return body["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:200]
            last = LLMError(f"HTTP {exc.code}: {detail}")
            if exc.code == 400 and any(k in payload for k in extra):
                for key in extra:
                    payload.pop(key, None)
                max_attempts = max(max_attempts, attempt + 1)
                continue
            if exc.code in (400, 401, 402, 403):
                break
        except Exception as exc:  # noqa: BLE001
            last = exc
            # 连不上（DNS/TCP）就别等三次，网络抖动两次足够
            if isinstance(exc, (urllib.error.URLError, OSError)):
                max_attempts = min(max_attempts, 2)
        if attempt < max_attempts and time.time() + 3 < deadline:
            time.sleep(2)
    raise LLMError(str(last)[:300])


def parse_json_loose(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        chunk = text[start : end + 1]
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            chunk = re.sub(r",\s*([}\]])", r"\1", chunk)
            return json.loads(chunk)
    raise LLMError("模型返回的不是 JSON")


def _article_block(idx: int, art: Article, detailed: bool, max_chars: int) -> str:
    body = truncate(art.text or art.excerpt, max_chars)
    date = art.published.strftime("%m月%d日") if art.published else ""
    return (
        f"[{idx}] 标题：{art.title}\n"
        f"来源：{art.source}｜语言：{'中文' if art.lang == 'zh' else '英文'}｜日期：{date}"
        f"｜{'详读' if detailed else '速览'}\n"
        f"正文节选：{body}\n"
    )


def summarize_section(
    section: dict,
    detailed: list[Article],
    brief: list[Article],
    cfg: dict,
) -> SectionDigest:
    digest = SectionDigest(
        key=section["key"],
        name=section["name"],
        cn=section.get("cn", section["name"]),
        blurb=section.get("blurb", ""),
        accent=section.get("accent", "#333333"),
    )
    all_arts = detailed + brief
    max_chars = int(cfg.get("max_chars_per_article", 1200))
    blocks = [
        _article_block(i + 1, art, i < len(detailed), max_chars)
        for i, art in enumerate(all_arts)
    ]
    user = (
        f"板块：{section['name']}（{section.get('cn', '')}）\n"
        f"本板块文章已按重要性排序，共 {len(all_arts)} 篇：前 {len(detailed)} 篇标为「详读」，其余为「速览」。\n\n"
        + "\n".join(blocks)
        + "\n写作要求：\n"
        f"1. 输出全部 {len(all_arts)} 条，按原编号顺序，不要增删。\n"
        "2. 「详读」条目写 3 组句子对；「速览」条目写 1 组句子对。\n"
        "3. 英文源：en 必须是正文里逐字出现的英文原句（可截取一句，不改写、不拼接）；zh 是这一句准确通顺的中文翻译，不是逐字硬译。\n"
        "4. 中文源：en 留空字符串，zh 写一句实质性概括或摘录，不要复述标题。\n"
        "5. headline_zh 是中文小标题，不超过 22 字，必须包含具体信息（谁、做了什么、数字）。\n"
        "6. why 用一句话说清这件事为什么值得关注，不超过 30 字。\n"
        "7. 不要编造正文里没有的事实、数字和引语。\n\n"
        + SCHEMA_HINT
    )
    try:
        raw = call_llm(cfg, SYSTEM_PROMPT, user)
        data = parse_json_loose(raw)
    except Exception as exc:  # noqa: BLE001 - 失败即降级
        digest.note = f"规则摘要（{str(exc)[:60]}）"
        return _rule_fill(digest, detailed, brief)

    by_index = {i + 1: art for i, art in enumerate(all_arts)}
    for entry in data.get("items", []):
        try:
            n = int(entry.get("n"))
        except (TypeError, ValueError):
            continue
        art = by_index.get(n)
        if not art:
            continue
        points: list[Point] = []
        for p in entry.get("points", [])[:4]:
            if not isinstance(p, dict):
                continue
            en = str(p.get("en", "")).strip()
            zh = str(p.get("zh", "")).strip()
            if art.lang == "zh":
                en = ""  # 中文源不该出现英文原句，模型串了就直接丢掉
            if en and not _quote_is_real(en, art.text or art.excerpt):
                en = ""  # 模型改写了原句，宁可不显示也不误导
            elif en:
                en = tidy_quote(en, art.text or art.excerpt)
            if NOISE_LINE.search(zh) and len(zh) < 40:
                zh = ""
            if NOISE_LINE.search(en) and len(en) < 40:
                en = ""
            if en or zh:
                points.append(Point(en=en, zh=zh))
        item = Item(
            headline=str(entry.get("headline_zh") or art.title).strip()[:40],
            points=points,
            why=str(entry.get("why", "")).strip()[:60],
            url=art.url,
            source=art.source,
            published=art.published,
            lang=art.lang,
            detailed=n <= len(detailed),
            sources_all=sorted({art.source, *art.duplicates}),
        )
        digest.items.append(item)
        (digest.detailed if item.detailed else digest.brief).append(item)
    digest.intro = str(data.get("intro", "")).strip()

    # 模型漏掉的条目用规则补上，保证数量
    covered = {it.url for it in digest.items}
    missing_detailed = [a for a in detailed if a.url not in covered]
    missing_brief = [a for a in brief if a.url not in covered]
    if missing_detailed or missing_brief:
        filler = SectionDigest(
            key=digest.key, name=digest.name, cn=digest.cn, blurb=digest.blurb, accent=digest.accent
        )
        _rule_fill(filler, missing_detailed, missing_brief)
        digest.detailed.extend(filler.detailed)
        digest.brief.extend(filler.brief)
        digest.items.extend(filler.items)
    if not digest.intro:
        digest.intro = f"本周 {section.get('cn', section['name'])} 领域共 {len(digest.items)} 条值得注意的进展。"
    return digest


TERMINAL = ".!?\"”’"


def tidy_quote(quote: str, source: str) -> str:
    """模型偶尔把句子截在半个从句上，退回到最后一个完整句。"""
    quote = quote.strip()
    if not quote or quote[-1] in TERMINAL:
        return quote
    idx = max(quote.rfind(c) for c in ".!?")
    if idx >= 40:
        trimmed = quote[: idx + 1].strip()
        if _quote_is_real(trimmed, source):
            return trimmed
    return quote


def _quote_is_real(quote: str, source: str) -> bool:
    if not quote or not source:
        return False
    q = normalize_for_match(quote)
    s = normalize_for_match(source)
    return bool(q) and q in s


NOISE_LINE = re.compile(
    r"(点击查看原文|阅读原文|点击阅读|点此查看|查看原文|原文链接|扫码关注|关注我们的|"
    r"read more|click here|continue reading)",
    re.I,
)


def _clean(text: str) -> str:
    lines = [ln for ln in (text or "").splitlines() if ln.strip() and not NOISE_LINE.search(ln)]
    return "\n".join(lines).strip()


def _rule_point(art: Article) -> list[Point]:
    sentences = split_sentences(_clean(art.text or art.excerpt))
    body = " ".join(sentences[:2]) if sentences else (art.excerpt or art.title)
    body = truncate(body, 160)
    if art.lang == "zh":
        return [Point(en="", zh=body)]
    return [Point(en=body, zh="")]


def _rule_fill(digest: SectionDigest, detailed: list[Article], brief: list[Article]) -> SectionDigest:
    for group, is_detailed in ((detailed, True), (brief, False)):
        for art in group:
            item = Item(
                headline=art.title,
                points=_rule_point(art),
                url=art.url,
                source=art.source,
                published=art.published,
                lang=art.lang,
                detailed=is_detailed,
                sources_all=sorted({art.source, *art.duplicates}),
            )
            digest.items.append(item)
            (digest.detailed if is_detailed else digest.brief).append(item)
    if not digest.items:
        digest.intro = "本周没有抓取到内容。"
    return digest


def write_opening(sections: list[SectionDigest], cfg: dict) -> str:
    """整期开场白：用各板块标题喂给模型，失败就用模板句。"""
    lines = []
    for sec in sections:
        tops = "；".join(it.headline for it in (sec.detailed or sec.brief)[:2])
        lines.append(f"{sec.cn}：{tops}")
    user = (
        "下面是本周四个板块的条目摘要。请写 2 句话作为整期周报的开场白，"
        "要像一个懂行的朋友在跟你聊天，指出本周最值得注意的一条主线，不要罗列板块。\n\n"
        + "\n".join(lines)
        + '\n\n输出 JSON：{"opening": "..."}'
    )
    try:
        data = parse_json_loose(call_llm(cfg, SYSTEM_PROMPT, user, max_tokens=300))
        text = str(data.get("opening", "")).strip()
        if text:
            return text
    except Exception:  # noqa: BLE001
        pass
    return ""


DEDUPE_PROMPT = """下面是同一周内几个板块的候选新闻标题（编号、板块、标题）。
其中有些是同一件事被不同媒体、不同语言报道，措辞完全不同。
请找出重复的组。每组用编号列表表示，把信息量最大、最适合保留的那条放在第一位。
判定标准：报道的是同一个具体事件（同一款产品、同一笔交易、同一个发布），
而不仅仅是同一个话题。宁可漏判，也不要误杀。
只输出 JSON：{"groups": [[3, 17], [22, 41, 55]]}
没有重复就输出 {"groups": []}。最多 20 组。"""


def find_duplicate_groups(listing: list[dict], cfg: dict) -> list[list[int]]:
    """让模型找出跨板块的同一事件，返回编号分组（1-based）。"""
    if len(listing) < 2:
        return []
    lines = "\n".join(
        f"#{i + 1} [{it['section']}] {it['title']}" for i, it in enumerate(listing)
    )
    try:
        data = parse_json_loose(call_llm(cfg, SYSTEM_PROMPT, DEDUPE_PROMPT + "\n\n" + lines, max_tokens=800))
    except Exception:  # noqa: BLE001
        return []
    groups: list[list[int]] = []
    for group in data.get("groups", []):
        try:
            idx = sorted({int(x) for x in group})
        except (TypeError, ValueError):
            continue
        idx = [i for i in idx if 1 <= i <= len(listing)]
        if len(idx) >= 2:
            groups.append(idx)
    return groups
