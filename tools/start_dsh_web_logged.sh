#!/usr/bin/env bash
# 批188 · DSH web 启动包装（日志落盘）：把 stdout/stderr 重定向到 ~/.dsh/logs/dsh-web.log
#   —— 现状：DSH 服务 stdout/stderr 只进 /dev/pts/1（终端），断流/崩溃**无痕**（2026-09-15 实测）。
# 用法（**下次重启 DSH 时**用它替代直接 pnpm dsh web）：
#   bash tools/start_dsh_web_logged.sh            # 前台
#   nohup bash tools/start_dsh_web_logged.sh &    # 后台
set -euo pipefail
LOG_DIR="$HOME/.dsh/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/dsh-web.log"
cd /home/<user>/deepseek-harness
echo "[$(date '+%F %T')] start dsh web (log -> $LOG)" | tee -a "$LOG"
exec pnpm dsh web "$@" >>"$LOG" 2>&1
