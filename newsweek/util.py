"""文本与时间工具：全部只用标准库。"""
from __future__ import annotations

import email.utils
import html
import re
import unicodedata
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))  # 北京时间，周报固定按这个时区算

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\u3000]+")
_NL_RE = re.compile(r"\n{2,}")
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def strip_html(text: str) -> str:
    """去掉标签、脚本样式、实体，压成干净的纯文本。"""
    if not text:
        return ""
    text = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</h\d>", "\n", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ").replace("\u200b", "")
    text = _CTRL_RE.sub("", text)
    text = "\n".join(_WS_RE.sub(" ", line).strip() for line in text.splitlines())
    text = _NL_RE.sub("\n\n", text)
    return text.strip()


def clean_title(title: str) -> str:
    title = strip_html(title or "")
    title = re.sub(r"\s+", " ", title).strip()
    return title


def normalize_for_match(text: str) -> str:
    """用于相似度比较：全角转半角、去标点、转小写。"""
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "", text)
    return text


def shingles(text: str, n: int = 3) -> set[str]:
    text = normalize_for_match(text)
    if len(text) <= n:
        return {text} if text else set()
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if not inter:
        return 0.0
    return inter / (len(a) + len(b) - inter)


def split_sentences(text: str) -> list[str]:
    """中英混排的粗分句，够用即可。"""
    text = (text or "").strip()
    if not text:
        return []
    # 英文句号后面必须跟空格或结尾，避免切开 3.5、U.S. 这类
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\u4e00-\u9fff\"'“(])|(?<=[。！？；])", text)
    out = [p.strip() for p in parts if p and p.strip()]
    return out


def parse_date(raw: str | None) -> datetime | None:
    """把各种 RSS/Atom 时间格式解析成带时区的 datetime。"""
    if not raw:
        return None
    raw = raw.strip()
    try:
        dt = email.utils.parsedate_to_datetime(raw)
        if dt:
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    candidate = raw.replace("Z", "+00:00")
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
    ):
        try:
            dt = datetime.strptime(candidate, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=TZ)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(candidate)
        return dt if dt.tzinfo else dt.replace(tzinfo=TZ)
    except Exception:
        return None


def local(dt: datetime | None) -> datetime | None:
    return dt.astimezone(TZ) if dt else None


def fmt_cn(dt: datetime | None) -> str:
    dt = local(dt)
    if not dt:
        return ""
    return f"{dt.month}月{dt.day}日"


def iso_week(dt: datetime) -> tuple[int, int]:
    y, w, _ = dt.isocalendar()
    return y, w


def week_label(dt: datetime) -> str:
    y, w = iso_week(dt)
    return f"{y}-W{w:02d}"


def week_range(dt: datetime) -> str:
    dt = local(dt)
    monday = dt - timedelta(days=dt.weekday())
    sunday = monday + timedelta(days=6)
    return f"{monday.month}月{monday.day}日 – {sunday.month}月{sunday.day}日"


def truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    # 尽量在句末截断
    for sep in ("。", "！", "？", ". ", "；", "; "):
        idx = cut.rfind(sep)
        if idx > limit * 0.6:
            return cut[: idx + len(sep)].strip()
    return cut.rstrip() + "…"


def word_count(text: str) -> int:
    """粗略 token 估计：中文按字，英文按词。"""
    en = len(re.findall(r"[A-Za-z']+", text or ""))
    zh = len(re.findall(r"[\u4e00-\u9fff]", text or ""))
    return en + zh
