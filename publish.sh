#!/bin/bash
# 本地生成 + 发布：不依赖 GitHub 的定时器。
# 流程：生成本周周报 → 提交 site/ → 推送到 GitHub → 推送动作会自动触发 Pages 部署。
# 由 install_schedule.sh 装成每周五 21:00 的 launchd 任务。
set -uo pipefail
cd "$(dirname "$0")" || exit 1

LOG_DIR="logs"
mkdir -p "$LOG_DIR"
STAMP=$(date "+%Y-%m-%d %H:%M:%S")
echo "===== $STAMP 开始" >> "$LOG_DIR/publish.log"

# 读 .env 里的 API Key
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

PY="$(command -v python3 || echo /usr/bin/python3)"

# 1) 生成（本周已生成过就跳过，不重复花钱）
"$PY" run.py --no-open --skip-if-done >> "$LOG_DIR/publish.log" 2>&1
GEN=$?
echo "生成退出码: $GEN" >> "$LOG_DIR/publish.log"
if [ $GEN -ne 0 ]; then
  echo "生成失败，保留现有线上内容" >> "$LOG_DIR/publish.log"
  exit 1
fi

# 2) 提交并推送（推送 site/ 会触发云端重新部署）
KEY="$PWD/.deploy_key/id_ed25519"
if [ ! -f "$KEY" ]; then
  echo "找不到部署密钥，跳过推送" >> "$LOG_DIR/publish.log"
  exit 0
fi

git add site >> "$LOG_DIR/publish.log" 2>&1
if git diff --staged --quiet; then
  echo "内容没有变化，跳过推送" >> "$LOG_DIR/publish.log"
  exit 0
fi
git -c user.name="weekly-brief-bot" -c user.email="bot@users.noreply.github.com" \
    commit -q -m "chore: 周报 $(date +%G-W%V)"

export GIT_SSH_COMMAND="ssh -i $KEY -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 -o UserKnownHostsFile=$PWD/.deploy_key/known_hosts -o ProxyCommand='nc -X connect -x 127.0.0.1:7890 %h %p'"
GIT_TERMINAL_PROMPT=0 git pull --rebase -q origin main >> "$LOG_DIR/publish.log" 2>&1
GIT_TERMINAL_PROMPT=0 git push origin main >> "$LOG_DIR/publish.log" 2>&1
PUSH=$?
echo "推送退出码: $PUSH" >> "$LOG_DIR/publish.log"
echo "===== $(date "+%Y-%m-%d %H:%M:%S") 结束" >> "$LOG_DIR/publish.log"
exit $PUSH
