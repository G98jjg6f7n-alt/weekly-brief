#!/bin/bash
# 双击运行：生成本周周报 → 推送到 GitHub（自动部署）→ 打开页面
cd "$(dirname "$0")" || exit 1

./publish.sh
STATUS=$?

if [ "${1:-}" != "--no-open" ] && [ -f site/index.html ]; then
  open site/index.html
fi

echo
if [ $STATUS -eq 0 ]; then
  echo "完成。云端页面：https://G98jjg6f7n-alt.github.io/weekly-brief/"
else
  echo "生成或推送失败，详情见 logs/publish.log"
fi
read -r -p "按回车关闭窗口"
exit $STATUS
