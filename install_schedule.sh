#!/bin/bash
# 在本机装一个周五 21:00 的定时任务（macOS launchd）。
# 和云端版不冲突：云端负责手机看，这个负责"打开电脑就有一份"。
# 用法：./install_schedule.sh          安装
#      ./install_schedule.sh --remove  卸载
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.weeklybrief.generate"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ "${1:-}" = "--remove" ]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "已卸载定时任务"
  exit 0
fi

PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
  echo "找不到 python3"; exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" "$DIR/logs"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>$DIR/run.py</string>
    <string>--no-open</string>
  </array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>5</integer>
    <key>Hour</key><integer>21</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key><string>$DIR/logs/launchd.log</string>
  <key>StandardErrorPath</key><string>$DIR/logs/launchd.err.log</string>
  <key>RunAtLoad</key><false/>
</dict>
</plist>
EOF

plutil -lint "$PLIST" >/dev/null
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST" 2>/dev/null || echo "（plist 已生成，但 launchctl 未能加载，请手动执行：launchctl load $PLIST）"
echo "已安装：每周五 21:00 自动生成（Mac 睡眠错过后会在唤醒时补跑）"
echo "日志：$DIR/logs/launchd.log"
