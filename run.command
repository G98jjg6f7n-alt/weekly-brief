#!/bin/bash
# 双击运行：生成本周周报并自动打开
cd "$(dirname "$0")" || exit 1

PY=""
for cand in python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  if command -v "$cand" >/dev/null 2>&1; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then
  echo "找不到 python3，请先安装（https://www.python.org/downloads/）"
  read -r -p "按回车退出"
  exit 1
fi

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

"$PY" run.py "$@"
STATUS=$?
echo
read -r -p "按回车关闭窗口"
exit $STATUS
