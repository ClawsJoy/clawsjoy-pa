#!/usr/bin/env bash
# 网关重启（硬编码 cd live，防从沙箱误启）
set -u
LIVE="/home/<user>/clawsjoy_v5"
cd "$LIVE" || { echo "无法 cd 到 live: $LIVE"; exit 1; }
PID=$(ss -tlnp 2>/dev/null | grep ':5002' | grep -oP 'pid=\K[0-9]+' | head -1)
if [ -n "$PID" ]; then kill "$PID" 2>/dev/null && echo "已停旧网关 pid=$PID"; fi
sleep 2
nohup python3 agent_gateway_enhanced.py > logs/gateway.log 2>&1 &
echo "网关已从 live 重启: $LIVE"
sleep 3
ss -tlnp 2>/dev/null | grep -q ':5002' && echo "端口 5002 UP" || echo "端口 5002 启动中(6-10s)"
