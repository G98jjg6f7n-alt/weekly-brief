#!/usr/bin/env python3
"""每周新闻周报 v2 · 命令行入口

  python3 run.py                 生成本周并打开（同一周已生成则直接打开）
  python3 run.py --force         重新生成
  python3 run.py --no-llm        不用模型，走规则兜底
  python3 run.py --serve         生成后起本地服务（支持追问接口）
  python3 run.py --no-open       只生成
"""
from __future__ import annotations

import os
import sys
import time
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def load_dotenv(path: str) -> None:
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_dotenv(os.path.join(ROOT, ".env"))

from newsweek.pipeline import build_issue, build_search_index, load_config, save_issue  # noqa: E402
from newsweek.render import write_site  # noqa: E402


def self_check(issue: dict, cfg: dict) -> list[str]:
    problems: list[str] = []
    n = sum(len(s["items"]) for s in issue["sections"])
    if n < int(cfg.get("min_items", 12)):
        problems.append(f"条目只有 {n} 条")
    if len(issue["sections"]) < 5:
        problems.append(f"只有 {len(issue['sections'])} 个栏目有内容")
    if issue.get("mode") == "llm" and not (issue.get("deep_dive") or {}).get("question"):
        problems.append("深度观察缺失")
    if len(issue.get("top_ids") or []) < 5:
        problems.append("首页头条不足 5 条")
    st = issue.get("stats", {})
    if st.get("sources_total") and st["sources_ok"] / st["sources_total"] < 0.5:
        problems.append(f"源成功率低：{st['sources_ok']}/{st['sources_total']}")
    return problems


def main(argv: list[str]) -> int:
    cfg = load_config()
    week = time.strftime("%G-W%V")
    data_file = os.path.join(ROOT, cfg.get("output", {}).get("dir", "site"), "data", f"{week}.json")
    existing = os.path.join(ROOT, cfg.get("output", {}).get("dir", "site"), "issues", f"{week}.html")

    if "--skip-if-done" in argv and os.path.isfile(data_file):
        print(f"本周（{week}）已生成，跳过生成")
        return 0

    interactive = "--no-open" not in argv and not os.environ.get("CI")
    if interactive and "--force" not in argv and os.path.isfile(existing):
        if time.time() - os.path.getmtime(existing) < 6 * 3600:
            print(f"本周已生成过：{existing}")
            webbrowser.open(f"file://{existing}")
            return 0

    started = time.time()
    issue = build_issue(cfg, no_llm="--no-llm" in argv)
    save_issue(issue, cfg)
    build_search_index(cfg)
    path = write_site(issue, cfg)

    problems = self_check(issue, cfg)
    print("⚠ 自检：" + "；".join(problems) if problems else "✓ 自检通过")
    print(f"\n已生成：{path}")
    print(f"本期 {issue['stats']['items']} 条，用时 {time.time() - started:.0f}s")

    if "--serve" in argv:
        from serve import serve

        serve(int(os.environ.get("PORT", "8000")))
    elif "--no-open" not in argv and sys.platform == "darwin":
        webbrowser.open(f"file://{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
