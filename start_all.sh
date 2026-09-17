#!/bin/bash
# ClawsJoy 全服务启动脚本
cd /home/flybo/clawsjoy_v5

echo "🚀 启动 ClawsJoy 全服务..."
echo ""

# 1. Ollama
if ! pgrep -f "ollama serve" > /dev/null; then
    echo "🦙 启动 Ollama..."
    ollama serve > /tmp/ollama.log 2>&1 &
    sleep 2
else
    echo "🦙 Ollama 已运行"
fi

# 2. Gateway (5002)
echo "🌐 启动 Gateway (5002)..."
pkill -f "agent_gateway_enhanced" 2>/dev/null
nohup python3 agent_gateway_enhanced.py > logs/gateway.log 2>&1 &
sleep 2

# 3. AI Studio (8502)
echo "🎯 启动 AI Studio (8502)..."
pkill -f "streamlit" 2>/dev/null
nohup streamlit run web/app_complete.py --server.port 8502 --server.address 0.0.0.0 > logs/streamlit.log 2>&1 &
sleep 2

# 4. Discord Bot
echo "💬 启动 Discord Bot..."
pkill -f "discord_bot_poll" 2>/dev/null
nohup python3.10 discord_bot_poll.py > logs/discord.log 2>&1 &

# 5. 数字人 (7860)
echo "🎭 启动数字人 (7860)..."
pkill -f "webui.py" 2>/dev/null
cd /home/flybo/clawsjoy_avatar/GMTalker
nohup bash -c "source /home/flybo/miniconda3/etc/profile.d/conda.sh && conda activate gmtalker && python webui.py" > /tmp/gmtalker.log 2>&1 &
cd /home/flybo/clawsjoy_v5

sleep 3
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 启动完成！"
echo "  Workbench : http://localhost:5002/workbench"
echo "  AI Studio : http://localhost:8502"
echo "  数字人    : http://localhost:7860"
echo "  Discord   : 已连接（轮询模式）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
