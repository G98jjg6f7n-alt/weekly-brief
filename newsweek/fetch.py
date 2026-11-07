"""抓取 RSS / Atom：容错解析、超时重试、并发拉取。"""
from __future__ import annotations

import concurrent.futures as cf
import gzip
import os
import socket
import hashlib
import io
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime

from .util import clean_title, local, parse_date, strip_html

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
_OPENER: urllib.request.OpenerDirector | None = None


def detect_proxy() -> str | None:
    """优先用环境变量；否则探测本机常见代理端口（Clash 7890 等）。"""
    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        if os.environ.get(key):
            return os.environ[key]
    for port in (7890, 7891, 1087, 6152, 8888):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return f"http://127.0.0.1:{port}"
        except OSError:
            continue
    return None


def set_proxy(url: str | None) -> None:
    global _OPENER
    if not url:
        _OPENER = None
        return
    handler = urllib.request.ProxyHandler({"http": url, "https": url})
    _OPENER = urllib.request.build_opener(handler)


ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1/}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"


@dataclass
class Article:
    title: str
    url: str
    source: str
    section: str
    lang: str
    published: datetime | None = None
    excerpt: str = ""
    body: str = ""
    html: str = ""
    image: dict | None = None
    weight: float = 1.0
    duplicates: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return hashlib.sha1((self.url or self.title).encode("utf-8")).hexdigest()[:12]

    @property
    def text(self) -> str:
        return self.body or self.excerpt


@dataclass
class SourceResult:
    name: str
    section: str
    ok: bool
    count: int = 0
    error: str = ""
    elapsed: float = 0.0


def _sanitize(raw: bytes) -> str:
    """修掉常见的坏 XML：非法控制字符、未转义的 &。"""
    text = raw.decode("utf-8", "replace")
    if text.startswith("\ufeff"):
        text = text[1:]
    text = re.sub(
        r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", text
    )
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text


def http_get(url: str, timeout: int = 20, retries: int = 2, referer: str = "") -> bytes:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            headers = {
                "User-Agent": UA,
                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Cache-Control": "no-cache",
            }
            if referer:
                headers["Referer"] = referer
            req = urllib.request.Request(url, headers=headers)
            opener = _OPENER or urllib.request.build_opener()
            with opener.open(req, timeout=timeout) as resp:
                data = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                return data
        except Exception as exc:  # noqa: BLE001 - 单源失败不应影响整体
            last = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last if last else RuntimeError("unknown error")


def _text(node, *paths: str) -> str:
    for path in paths:
        found = node.find(path)
        if found is not None and (found.text or "").strip():
            return found.text.strip()
    return ""


def _link(node) -> str:
    links = node.findall("link") + node.findall(f"{ATOM}link")
    for link in links:
        if link.text and link.text.strip():
            return link.text.strip()
    for link in links:
        href = link.get("href")
        if href and link.get("rel", "alternate") in ("alternate", ""):
            return href.strip()
    if links and links[0].get("href"):
        return links[0].get("href").strip()
    guid = _text(node, "guid", f"{ATOM}id")
    if guid.startswith("http"):
        return guid
    return ""


def _parse_items(root) -> list:
    items = root.findall(".//item")
    if items:
        return items
    return root.findall(f".//{ATOM}entry")


def _regex_fallback(text: str) -> list[dict]:
    """XML 彻底解析失败时的兜底：直接正则抠条目。"""
    out: list[dict] = []
    for block in re.findall(r"(?is)<item\b.*?</item>|<entry\b.*?</entry>", text)[:80]:
        title = re.search(r"(?is)<title[^>]*>(.*?)</title>", block)
        link = re.search(r"(?is)<link[^>]*href=[\"']([^\"']+)[\"']", block) or re.search(
            r"(?is)<link[^>]*>(.*?)</link>", block
        )
        date = re.search(
            r"(?is)<(pubDate|published|updated|dc:date)[^>]*>(.*?)</\1>", block
        )
        desc = re.search(r"(?is)<(description|summary|content)[^>]*>(.*?)</\1>", block)
        out.append(
            {
                "title": clean_title(strip_html(title.group(1))) if title else "",
                "link": (link.group(1).strip() if link else ""),
                "date": date.group(2).strip() if date else "",
                "excerpt": strip_html(desc.group(2)) if desc else "",
            }
        )
    return out


def parse_feed(raw: bytes) -> tuple[list[dict], str]:
    """返回 (条目列表, 使用的解析方式)。"""
    text = _sanitize(raw)
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return _regex_fallback(text), "regex"

    records: list[dict] = []
    for node in _parse_items(root):
        title = clean_title(
            _text(node, "title", f"{ATOM}title", f"{DC}title")
        )
        url = _link(node)
        if not title or not url:
            continue
        date_raw = _text(
            node,
            "pubDate",
            f"{DC}date",
            f"{ATOM}published",
            f"{ATOM}updated",
            "published",
            "updated",
        )
        desc = _text(
            node,
            "description",
            f"{CONTENT}encoded",
            f"{ATOM}summary",
            f"{ATOM}content",
            "summary",
            "content",
        )
        records.append(
            {
                "title": title,
                "link": url,
                "date": date_raw,
                "excerpt": strip_html(desc),
            }
        )
    return records, "xml"


def looks_chinese(text: str) -> bool:
    if not text:
        return False
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return cjk >= max(6, latin * 0.4)


def fetch_source(source: dict, section: str, window_days: int = 8) -> tuple[list[Article], SourceResult]:
    name = source["name"]
    started = time.time()
    result = SourceResult(name=name, section=section, ok=False)
    try:
        raw = http_get(source["url"], timeout=source.get("timeout", 20))
        records, mode = parse_feed(raw)
        result.count = len(records)
        articles: list[Article] = []
        cutoff = time.time() - window_days * 86400
        lang_default = source.get("lang", "en")
        keywords = [k.lower() for k in source.get("keywords", [])]
        for rec in records:
            published = parse_date(rec.get("date"))
            if published and published.timestamp() < cutoff:
                continue
            excerpt = rec.get("excerpt", "")
            if keywords:
                haystack = (rec["title"] + " " + excerpt).lower()
                if not any(k in haystack for k in keywords):
                    continue
            lang = source.get("lang") or ("zh" if looks_chinese(rec["title"] + excerpt) else lang_default)
            articles.append(
                Article(
                    title=rec["title"],
                    url=rec["link"],
                    source=name,
                    section=section,
                    lang=lang,
                    published=local(published),
                    excerpt=excerpt,
                    weight=float(source.get("weight", 1.0)),
                )
            )
        result.ok = True
        if mode == "regex":
            result.error = "XML 损坏，已用正则兜底"
        return articles, result
    except Exception as exc:  # noqa: BLE001
        result.error = f"{type(exc).__name__}: {exc}"[:160]
        return [], result
    finally:
        result.elapsed = round(time.time() - started, 1)


def fetch_all(config: dict, allow_intl: bool = True) -> tuple[list[Article], list[SourceResult]]:
    """并发抓取所有源，返回文章和每个源的健康状况。"""
    window = int(config.get("window_days", 8))
    jobs = []
    for section in config["sections"]:
        for source in section["sources"]:
            if source.get("disabled"):
                continue
            if not allow_intl and source.get("region") == "intl":
                continue
            jobs.append((source, section["key"]))

    articles: list[Article] = []
    results: list[SourceResult] = []
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(fetch_source, src, sec, window): (src, sec) for src, sec in jobs
        }
        for fut in cf.as_completed(futures):
            src, sec = futures[fut]
            try:
                items, res = fut.result()
            except Exception as exc:  # noqa: BLE001
                items, res = [], SourceResult(name=src["name"], section=sec, ok=False, error=str(exc)[:160])
            articles.extend(items)
            results.append(res)
    results.sort(key=lambda r: (r.section, r.name))
    return articles, results
