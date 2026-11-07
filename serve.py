#!/usr/bin/env python3
"""本地服务：静态站 + 追问接口。

    python3 serve.py          # http://127.0.0.1:8000
手机同一 WiFi 也可访问（启动时会打印局域网地址）。

追问接口只在本地可用；部署到 GitHub Pages 时页面会提示需要本地服务。
"""
from __future__ import annotations

import json
import os
import socket
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def _load_env() -> None:
    path = os.path.join(ROOT, ".env")
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_LOADED = False


def ask(payload: dict) -> dict:
    global _LOADED
    if not _LOADED:
        _load_env()
        _LOADED = True

    from newsweek.llm import call_llm, LLMError
    from newsweek.pipeline import load_config

    cfg = load_config().get("llm", {})
    q = (payload.get("question") or "").strip()[:500]
    if not q:
        return {"error": "问题为空"}
    context = (
        f"新闻标题：{payload.get('headline','')}\n"
        f"摘要：{payload.get('summary','')}\n"
        f"期号：{payload.get('issue','')}\n"
    )
    system = (
        "你是《WEEKLY BRIEF》的观察者，读者是中国高中生。"
        "回答他的追问：直接给判断，说明依据，指出不确定之处；"
        "如果他的问题里含有错误前提，先温和地纠正。"
        "不要写套话，不要超过 300 字，用中文，必要时保留英文专有名词。"
    )
    user = f"{context}\n读者的追问：{q}"
    try:
        return {"answer": call_llm(cfg, system, user, max_tokens=800, json_mode=False).strip()}
    except LLMError as exc:
        return {"error": f"模型不可用：{exc}"[:200]}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=os.path.join(ROOT, "site"), **kw)

    def log_message(self, fmt, *args):  # 安静
        pass

    def do_POST(self):
        if self.path != "/api/ask":
            self.send_error(404)
            return
        try:
            n = int(self.headers.get("content-length", 0))
            payload = json.loads(self.rfile.read(n) or b"{}")
            result = ask(payload)
        except Exception as exc:  # noqa: BLE001
            result = {"error": f"服务异常：{exc}"[:200]}
        data = json.dumps(result, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve(port: int = 8000) -> None:
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"本地预览：http://127.0.0.1:{port}/   （Ctrl+C 结束）")
    try:
        ip = socket.gethostbyname(socket.gethostname())
        print(f"同一 WiFi 下的手机：http://{ip}:{port}/")
    except Exception:  # noqa: BLE001
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", "8000")))
