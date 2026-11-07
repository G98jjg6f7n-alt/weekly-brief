"""DeepSeek 客户端：JSON 输出、失败重试、用量统计。"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request

USAGE = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}


class LLMError(RuntimeError):
    pass


def usage_summary() -> dict:
    return dict(USAGE)


def _post(url: str, payload: dict, key: str, timeout: int) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def call_llm(
    cfg: dict, system: str, user: str, max_tokens: int | None = None, json_mode: bool = True
) -> str:
    key = os.environ.get(cfg.get("api_key_env", "DEEPSEEK_API_KEY"), "").strip()
    if not key:
        raise LLMError("no api key")
    base = (os.environ.get("DEEPSEEK_BASE_URL") or cfg.get("base_url", "https://api.deepseek.com")).rstrip("/")
    payload = {
        "model": os.environ.get("DEEPSEEK_MODEL") or cfg.get("model", "deepseek-flash"),
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": cfg.get("temperature", 0.3),
        "max_tokens": max_tokens or cfg.get("max_tokens", 6000),
        "stream": False,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    extra = dict(cfg.get("extra_body") or {})
    payload.update(extra)

    last: Exception | None = None
    deadline = time.time() + float(cfg.get("deadline_seconds", 900))
    attempts = 3
    attempt = 0
    while attempt < attempts:
        attempt += 1
        if time.time() > deadline:
            raise LLMError(f"超时放弃：{last}")
        try:
            body = _post(f"{base}/chat/completions", payload, key, cfg.get("timeout", 180))
            usage = body.get("usage") or {}
            USAGE["prompt_tokens"] += int(usage.get("prompt_tokens", 0))
            USAGE["completion_tokens"] += int(usage.get("completion_tokens", 0))
            USAGE["calls"] += 1
            return body["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:200]
            last = LLMError(f"HTTP {exc.code}: {detail}")
            if exc.code == 400 and any(k in payload for k in extra):
                for k in extra:
                    payload.pop(k, None)
                attempts = max(attempts, attempt + 1)
                continue
            if exc.code in (400, 401, 402, 403):
                break
        except Exception as exc:  # noqa: BLE001
            last = exc
            if isinstance(exc, (urllib.error.URLError, OSError)):
                attempts = min(attempts, 2)
        if attempt < attempts and time.time() + 3 < deadline:
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
            return json.loads(re.sub(r",\s*([}\]])", r"\1", chunk))
    raise LLMError("模型返回的不是 JSON")
