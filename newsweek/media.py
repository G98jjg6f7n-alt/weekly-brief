"""图片：从文章页取原图、校验尺寸与相关性、去重。

原则：
- 只用报道方自己发布的图片（og:image / 正文首图），不去搜图、不生成图；
- 校验真实像素尺寸与横构图，过小或竖图直接丢弃；
- 图注只写「报道配图」+ 来源，不编造画面内容；
- 找不到合格图片就不放图，绝不用占位图凑数。
"""
from __future__ import annotations

import hashlib
import re
import struct
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .fetch import http_get

# 按路径段匹配，避免把 uploads/ 这种正常路径误杀（ad 不是随便出现的）
BAD_WORDS = re.compile(
    r"(^|[/_.-])(logo|icon|favicon|avatar|sprite|placeholder|blank|spacer|qr|qrcode|"
    r"banner|advert|ads?|share|wechat|weibo|loading|default|watermark|emoji|button)([/_.-]|$)",
    re.I,
)
GOOD_EXT = re.compile(r"\.(jpe?g|png|webp)(\?|$)", re.I)


@dataclass
class Picture:
    url: str
    alt: str = ""
    width: int = 0
    height: int = 0


def _dims_jpeg(data: bytes) -> tuple[int, int]:
    i = 2
    n = len(data)
    while i < n - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h, w = struct.unpack(">HH", data[i + 5 : i + 9])
            return w, h
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        seg = struct.unpack(">H", data[i + 2 : i + 4])[0]
        i += 2 + seg
    return 0, 0


def _dims_png(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or data[12:16] != b"IHDR":
        return 0, 0
    return struct.unpack(">II", data[16:24])


def _dims_webp(data: bytes) -> tuple[int, int]:
    if len(data) < 30:
        return 0, 0
    chunk = data[12:16]
    if chunk == b"VP8X":
        w = int.from_bytes(data[24:27], "little") + 1
        h = int.from_bytes(data[27:30], "little") + 1
        return w, h
    if chunk == b"VP8 ":
        w, h = struct.unpack("<HH", data[26:30])
        return w & 0x3FFF, h & 0x3FFF
    if chunk == b"VP8L":
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return 0, 0


def probe_image(url: str, timeout: int = 8, max_bytes: int = 400_000) -> Picture | None:
    if not url or BAD_WORDS.search(url):
        return None
    try:
        data = http_get(url, timeout=timeout, retries=0)[:max_bytes]
    except Exception:  # noqa: BLE001
        return None
    w = h = 0
    if data[:2] == b"\xff\xd8":
        w, h = _dims_jpeg(data)
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = _dims_png(data)
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        w, h = _dims_webp(data)
    else:
        return None
    if not w or not h:
        return None
    if w < 600 or h < 240:  # 太窄或太矮
        return None
    ratio = w / h
    if ratio < 1.05 or ratio > 3.4:  # 竖图、长条 banner 都不要
        return None
    return Picture(url=url, width=w, height=h)


def pick(html_text: str, page_url: str, limit: int = 3) -> list[Picture]:
    """从文章 HTML 里取候选图（按 og:image → twitter:image → 正文 img 排序）。"""
    images: list[tuple[str, str]] = []
    for prop in ("og:image", "og:image:url", "twitter:image", "twitter:image:src"):
        m = re.search(
            r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]+content=["\']([^"\']+)' % re.escape(prop),
            html_text,
            re.I,
        )
        if not m:
            m = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']%s["\']' % re.escape(prop),
                html_text,
                re.I,
            )
        if m:
            images.append((m.group(1), ""))
            break

    for m in re.finditer(r"<img\b[^>]*>", html_text, re.I):
        tag = m.group(0)
        src = re.search(r'\b(?:data-src|data-original|data-lazy-src|src)=["\']([^"\']+)["\']', tag, re.I)
        if not src:
            continue
        # 页面上大量 logo/图标，先按标签自带的尺寸快速排除
        w_attr = re.search(r'\bwidth=["\']?(\d+)', tag, re.I)
        h_attr = re.search(r'\bheight=["\']?(\d+)', tag, re.I)
        if w_attr and int(w_attr.group(1)) < 400:
            continue
        if h_attr and int(h_attr.group(1)) < 200:
            continue
        alt = re.search(r'\balt=["\']([^"\']*)["\']', tag, re.I)
        images.append((src.group(1), (alt.group(1) if alt else "").strip()))
        if len(images) >= 40:
            break

    out: list[Picture] = []
    seen: set[str] = set()
    for src, alt in images:
        src = src.strip()
        if not src or src.startswith("data:"):
            continue
        full = urljoin(page_url, src)
        if not full.startswith("http") or not GOOD_EXT.search(full):
            continue
        key = hashlib.sha1(full.encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        pic = probe_image(full)
        if pic:
            pic.alt = alt[:80]
            out.append(pic)
        if len(out) >= limit or len(seen) > 10:
            break
    return out
