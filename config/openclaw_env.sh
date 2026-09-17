#!/bin/bash
# ClawsJoy - OpenClaw 环境配置
# 用途：配置 OpenClaw 使用 ClawsJoy Skills
# 用法：source /home/flybo/clawsjoy/config/openclaw_env.sh

export CLAWSJOY_HOME="/home/flybo/clawsjoy"
export OPENCLAW_SKILLS="/root/.openclaw/skills"

# ClawsJoy Skills 列表
export CLAWSJOY_SKILLS_LIST="auth billing coffee executor memory auto_generated promo queue router spider task tenant"

# OpenClaw Gateway 配置
export OPENCLAW_GATEWAY_PORT=18789
export OPENCLAW_GATEWAY_HOST="localhost"

# API 端点配置
export CLAWSJOY_AUTH_API="http://localhost:8092"
export CLAWSJOY_TENANT_API="http://localhost:8088"
export CLAWSJOY_BILLING_API="http://localhost:8090"
export CLAWSJOY_PROMO_API="http://localhost:8086"
export CLAWSJOY_COFFEE_API="http://localhost:8085"
export CLAWSJOY_TASK_API="http://localhost:8084"

# 宣传片配置
export CLAWSJOY_PROMO_ENDPOINT="${CLAWSJOY_TASK_API}/api/task/promo"
export CLAWSJOY_DEFAULT_CITY="香港"
export CLAWSJOY_DEFAULT_STYLE="科技"

# 日志级别
export CLAWSJOY_LOG_LEVEL="info"

echo "✅ ClawsJoy OpenClaw 环境已加载"
echo "   Skills 目录: $OPENCLAW_SKILLS"
echo "   API 网关: $CLAWSJOY_TASK_API"
