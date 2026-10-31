#!/bin/bash
# 一键把本项目推到 GitHub，并提示剩下两步手动操作。
# 用法：
#   ./deploy.sh                 交互式，会问你的用户名和仓库名
#   ./deploy.sh 用户名 仓库名    直接指定
#   ./deploy.sh --dry-run       只打印命令，不真的执行
set -euo pipefail
cd "$(dirname "$0")"

DRY=0
if [ "${1:-}" = "--dry-run" ]; then
  DRY=1
  shift
fi

say() { printf '\033[1m%s\033[0m\n' "$*"; }
run() {
  if [ "$DRY" = "1" ]; then
    echo "  \$ $*"
  else
    "$@"
  fi
}

USER_NAME="${1:-}"
REPO="${2:-}"

if [ -z "$USER_NAME" ]; then
  read -r -p "GitHub 用户名: " USER_NAME
fi
if [ -z "$REPO" ]; then
  read -r -p "仓库名（回车默认 weekly-brief）: " REPO
  REPO="${REPO:-weekly-brief}"
fi

say "1/4 检查 git 身份"
if ! git config user.email >/dev/null 2>&1; then
  run git config user.email "${USER_NAME}@users.noreply.github.com"
  run git config user.name "$USER_NAME"
fi

say "2/4 初始化仓库"
if [ ! -d .git ]; then
  run git init -b main
fi
run git add -A
run git commit -m "feat: 每周新闻周报（AI/汽车/数码/摄影）" || echo "  （没有新改动，跳过提交）"

say "3/4 关联远程仓库"
if git remote get-url origin >/dev/null 2>&1; then
  echo "  已有 origin：$(git remote get-url origin)"
else
  run git remote add origin "https://github.com/${USER_NAME}/${REPO}.git"
fi

say "4/4 推送"
run git push -u origin main

cat <<EOF

$( [ "$DRY" = "1" ] && echo "（以上是干跑，什么都没执行）" )

接下来只剩三步手动操作：

  1. 创建仓库（如果还没有）：https://github.com/new
     名字填 ${REPO}，可见性选 Public（Pages 免费版只支持公开仓库）

  2. 加密钥：仓库 → Settings → Secrets and variables → Actions → New repository secret
     名字 DEEPSEEK_API_KEY，值是你的 key
     （想要手机推送再加一个 BARK_URL）

  3. 开启 Pages：仓库 → Settings → Pages → Source 选 "GitHub Actions"
     然后到 Actions 页面点一次 "Run workflow"

网址会是：https://${USER_NAME}.github.io/${REPO}/
EOF
