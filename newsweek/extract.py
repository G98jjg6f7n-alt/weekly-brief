"""从文章页提取正文：轻量级 readability，只用标准库。"""
from __future__ import annotations

import re
from html.parser import HTMLParser

from .fetch import http_get
from .util import strip_html

SKIP_TAGS = {
    "script", "style", "noscript", "iframe", "svg", "form", "button",
    "nav", "header", "footer", "aside", "select", "textarea",
}
BLOCK_TAGS = {
    "p", "div", "section", "article", "main", "li", "td", "blockquote",
    "h1", "h2", "h3", "h4", "h5", "h6", "pre",
}
VOID_TAGS = {"br", "hr", "img", "input", "meta", "link", "source", "track", "wbr"}
POSITIVE_HINTS = re.compile(
    r"(article|content|post|entry|story|body|main|text|detail|rich_media|js_content)",
    re.I,
)
NEGATIVE_HINTS = re.compile(
    r"(comment|share|related|recommend|sidebar|advert|banner|footer|header|nav|menu|subscribe|"
    r"newsletter|popup|modal|cookie|social|tags|author-box|breadcrumb)",
    re.I,
)


class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag: str, attrs: dict | None = None, parent: "Node | None" = None):
        self.tag = tag
        self.attrs = attrs or {}
        self.children: list["Node | str"] = []
        self.parent = parent

    def text(self) -> str:
        parts: list[str] = []
        for child in self.children:
            parts.append(child if isinstance(child, str) else child.text())
        return "".join(parts)

    def find_all(self, tag: str):
        for child in self.children:
            if isinstance(child, Node):
                if child.tag == tag:
                    yield child
                yield from child.find_all(tag)

    def cls_id(self) -> str:
        return f"{self.attrs.get('class', '')} {self.attrs.get('id', '')}"


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            return
        node = Node(tag, dict(attrs), self.stack[-1])
        self.stack[-1].children.append(node)
        self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        return

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if data.strip():
            self.stack[-1].children.append(data)


def _prune(node: Node) -> None:
    """只按标签剪枝。实测不少站点 HTML 嵌套是坏的，按 class 删节点会连带正文一起删掉。"""
    kept: list[Node | str] = []
    for child in node.children:
        if isinstance(child, str):
            kept.append(child)
            continue
        if child.tag in SKIP_TAGS:
            continue
        _prune(child)
        kept.append(child)
    node.children = kept


def _score(node: Node) -> float:
    text = ""
    for p in node.find_all("p"):
        text += p.text()
    if len(text) < 120:
        # 有些站点不用 <p>，退化成直接统计块级文本
        text = "".join(
            c.text() for c in node.children if isinstance(c, Node) and c.tag in BLOCK_TAGS
        )
    if not text:
        return 0.0
    score = len(text)
    link_text = "".join(a.text() for a in node.find_all("a"))
    if text:
        score *= max(0.15, 1 - len(link_text) / max(len(text), 1) * 1.2)
    hint = node.cls_id()
    if POSITIVE_HINTS.search(hint):
        score *= 1.35
    if NEGATIVE_HINTS.search(hint):
        score *= 0.4
    if node.tag in ("article", "main"):
        score *= 1.2
    return score


def extract_text(html_text: str, min_len: int = 200) -> str:
    builder = _Builder()
    try:
        builder.feed(html_text)
    except Exception:  # noqa: BLE001 - 半截 HTML 也要能用
        pass
    root = builder.root
    _prune(root)

    body = next(root.find_all("body"), root)
    candidates = (
        list(body.find_all("div"))
        + list(body.find_all("article"))
        + list(body.find_all("main"))
        + list(body.find_all("section"))
    )
    best, best_score = None, 0.0
    for node in candidates:
        score = _score(node)
        if score > best_score:
            best, best_score = node, score
    if best is None or best_score < min_len:
        best = body

    text = _collect(best)
    if len(text) < 300:
        # 正文块没定位准，退回全页段落兜底
        text = _collect(body)
    if len(text) < 300 and best is not body:
        text = _collect(best) or text
    return text.strip()


BOILERPLATE = re.compile(
    r"^(subscribe|sign up|sign in|log in|read more|share this|advertisement|"
    r"follow us|download the app|click here|copyright|all rights reserved|"
    r"点击|扫码|关注我们|广告|责任编辑|本文来自|原标题)",
    re.I,
)


def _collect(node: Node) -> str:
    chunks: list[str] = []
    for tag in ("h2", "h3", "p", "li", "blockquote"):
        for sub in node.find_all(tag):
            text = re.sub(r"\s+", " ", sub.text()).strip()
            if len(text) < 25 or BOILERPLATE.search(text):
                continue
            chunks.append(text)
    seen: set[str] = set()
    out: list[str] = []
    for chunk in chunks:
        key = chunk[:40]
        if key in seen:
            continue
        seen.add(key)
        out.append(chunk)
    return "\n".join(out)


def fetch_body(url: str, timeout: int = 15) -> str:
    """抓取文章页并提取正文；失败返回空串，由调用方回退到 RSS 摘要。"""
    try:
        raw = http_get(url, timeout=timeout, retries=0)
        html_text = raw.decode("utf-8", "replace")
        head = html_text[:3000].lower()
        if "charset=gb" in head or "charset=\"gb" in head:
            html_text = raw.decode("gb18030", "replace")
        return extract_text(html_text)
    except Exception:  # noqa: BLE001
        return ""
