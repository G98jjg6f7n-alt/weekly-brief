#!/usr/bin/env python3
"""每周新闻周报 · 命令行入口

用法：
  python3 run.py                 # 生成本周周报并自动打开
  python3 run.py --no-llm        # 不用大模型，纯规则摘要（离线可用）
  python3 run.py --no-open       # 只生成不打开
  python3 run.py --serve         # 生成后起本地服务，手机连同一 WiFi 可看
  python3 run.py --only ai,photo # 只生成部分板块（调试用）
  python3 run.py --check         # 只做自检，不重新抓取
"""
from __future__ import annotations

import os
import sys
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def load_dotenv(path: str) -> None:
    """把项目根目录的 .env 读进环境变量，已设置的不覆盖。"""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv(os.path.join(ROOT, ".env"))

from newsweek.notify import notify  # noqa: E402
from newsweek.pipeline import build_issue, load_config, log, save_issue  # noqa: E402
from newsweek.render import render_issue, write_site  # noqa: E402

MIN_ITEMS_PER_SECTION = 4


def self_check(issue: dict, html_text: str, cfg: dict) -> list[str]:
    problems: list[str] = []
    want = {s["key"] for s in cfg["sections"]}
    got = {s["key"] for s in issue["sections"]}
    if len(got) < len(want) and want - got and len(got) > 1:
        problems.append(f"缺少板块：{', '.join(sorted(want - got))}")
    total = 0
    for sec in issue["sections"]:
        n = len(sec["items"])
        total += n
        if n < MIN_ITEMS_PER_SECTION:
            problems.append(f"{sec['cn']} 只有 {n} 条")
        if not any(it.get("detailed") for it in sec["items"]):
            problems.append(f"{sec['cn']} 没有详读条目")
    if total < 12:
        problems.append(f"整期只有 {total} 条")
    if len(html_text) < 15000:
        problems.append(f"页面只有 {len(html_text)} 字节，可能渲染不完整")
    if "__BODY__" in html_text or "__TITLE__" in html_text:
        problems.append("模板占位符未替换")
    stats = issue.get("stats", {})
    if stats.get("sources_total") and stats["sources_ok"] / stats["sources_total"] < 0.6:
        problems.append(f"只有 {stats['sources_ok']}/{stats['sources_total']} 个源抓取成功")
    return problems


def serve(directory: str, port: int = 8000) -> None:
    os.chdir(directory)

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):  # 安静一点
            pass

    with ThreadingHTTPServer(("0.0.0.0", port), Handler) as httpd:
        print(f"本地预览：http://127.0.0.1:{port}/   （Ctrl+C 结束）")
        try:
            import socket

            ip = socket.gethostbyname(socket.gethostname())
            print(f"同一 WiFi 下的手机可访问：http://{ip}:{port}/")
        except Exception:  # noqa: BLE001
            pass
        httpd.serve_forever()


def main(argv: list[str]) -> int:
    cfg = load_config()
    no_llm = "--no-llm" in argv

    week = time.strftime("%G-W%V")
    data_file = os.path.join(ROOT, cfg.get("output", {}).get("dir", "site"), "data", f"{week}.json")
    if "--skip-if-done" in argv and os.path.isfile(data_file):
        print(f"本周（{week}）已生成过，跳过抓取，直接部署现有内容")
        return 0
    existing = os.path.join(ROOT, cfg.get("output", {}).get("dir", "site"), "issues", f"{week}.html")
    interactive = "--no-open" not in argv and not os.environ.get("CI")
    if (
        interactive
        and "--force" not in argv
        and os.path.isfile(existing)
        and time.time() - os.path.getmtime(existing) < 6 * 3600
    ):
        print(f"本周周报已经生成过了：{existing}")
        print("想重新抓一遍就加 --force")
        webbrowser.open(f"file://{existing}")
        return 0
    only = None
    if "--only" in argv:
        only = argv[argv.index("--only") + 1].split(",")

    started = time.time()
    issue = build_issue(cfg, no_llm=no_llm, only=only)
    html_text = render_issue(issue, cfg)
    preview = bool(only)  # 调试某个板块时不要覆盖正式站点和归档
    # 先落数据再渲染，否则归档页读不到本期
    save_issue(issue, cfg, preview=preview)
    path = write_site(issue, html_text, cfg, preview=preview)

    problems = self_check(issue, html_text, cfg)
    if preview:
        problems = [p for p in problems if "条" not in p]
    if problems:
        log("⚠ 自检提示：" + "；".join(problems))
    else:
        log("✓ 自检通过")

    page_url = os.environ.get("PAGE_URL", "").strip()
    for line in notify(issue, cfg, page_url):
        log(f"  推送 {line}")

    print(f"\n已生成：{path}")
    print(f"本期 {sum(len(s['items']) for s in issue['sections'])} 条，用时 {time.time() - started:.0f}s")

    if "--serve" in argv:
        render_dir = os.path.join(ROOT, cfg.get("output", {}).get("dir", "site"))
        serve(render_dir, int(os.environ.get("PORT", "8000")))
    elif "--no-open" not in argv and sys.platform == "darwin":
        webbrowser.open(f"file://{path}")
    return 1 if problems and "--strict" in argv else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
