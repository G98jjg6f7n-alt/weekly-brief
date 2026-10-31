"""推送：Bark（iOS）、Server 酱（微信）、自定义 webhook。失败不影响周报生成。"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request


def _get(url: str, timeout: int = 10) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "weekly-brief/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")[:300]


def _post(url: str, payload: dict, timeout: int = 10) -> str:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")[:300]


def notify(issue: dict, cfg: dict, page_url: str = "") -> list[str]:
    """返回每条推送的结果描述，便于日志排查。"""
    conf = cfg.get("notify", {}) or {}
    title = f"{cfg.get('title', 'WEEKLY BRIEF')} · {issue['week']}"
    count = sum(len(s["items"]) for s in issue["sections"])
    body = issue.get("opening") or f"本期 {count} 条，约 {issue.get('range', '')}"
    results: list[str] = []

    bark = os.environ.get("BARK_URL", "").strip() or conf.get("bark_url", "").strip()
    if bark:
        try:
            base = bark.rstrip("/")
            url = f"{base}/{urllib.parse.quote(title)}/{urllib.parse.quote(body[:120])}"
            if page_url:
                url += f"?url={urllib.parse.quote(page_url)}"
            _get(url)
            results.append("Bark ✓")
        except Exception as exc:  # noqa: BLE001
            results.append(f"Bark × {type(exc).__name__}")

    serverchan = os.environ.get("SERVERCHAN_KEY", "").strip() or conf.get("serverchan_key", "").strip()
    if serverchan:
        try:
            url = f"https://sctapi.ftqq.com/{serverchan}.send"
            data = urllib.parse.urlencode({"title": title, "desp": body + (f"\n\n{page_url}" if page_url else "")})
            req = urllib.request.Request(url, data=data.encode(), method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
            results.append("Server酱 ✓")
        except Exception as exc:  # noqa: BLE001
            results.append(f"Server酱 × {type(exc).__name__}")

    webhook = os.environ.get("WEBHOOK_URL", "").strip() or conf.get("webhook", "").strip()
    if webhook:
        try:
            _post(webhook, {"title": title, "text": body, "url": page_url, "week": issue["week"]})
            results.append("Webhook ✓")
        except Exception as exc:  # noqa: BLE001
            results.append(f"Webhook × {type(exc).__name__}")

    return results
