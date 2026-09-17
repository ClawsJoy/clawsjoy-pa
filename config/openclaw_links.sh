#!/bin/bash
# ClawsJoy - OpenClaw 软链接配置模块
# 用法：source /home/flybo/clawsjoy/config/openclaw_links.sh && setup_links

setup_links() {
    echo "🔗 配置 ClawsJoy → OpenClaw 软链接..."
    
    local CLAWSJOY_SKILLS="/home/flybo/clawsjoy/skills"
    local OPENCLAW_SKILLS="/root/.openclaw/skills"
    
    # 创建目录
    mkdir -p "$OPENCLAW_SKILLS"
    cd "$OPENCLAW_SKILLS"
    
    # 清理旧链接
    find . -maxdepth 1 -type l -exec rm -f {} \;
    
    # 创建软链接
    for skill in auth billing coffee executor memory auto_generated promo queue router spider task tenant; do
        if [ -d "$CLAWSJOY_SKILLS/$skill" ]; then
            ln -sf "$CLAWSJOY_SKILLS/$skill" "$skill"
            echo "  ✅ $skill"
        fi
    done
    
    echo "✅ 软链接配置完成"
}

remove_links() {
    echo "🔗 移除 ClawsJoy → OpenClaw 软链接..."
    local OPENCLAW_SKILLS="/root/.openclaw/skills"
    
    if [ -d "$OPENCLAW_SKILLS" ]; then
        cd "$OPENCLAW_SKILLS"
        find . -maxdepth 1 -type l -exec rm -f {} \;
        echo "✅ 软链接已移除"
    fi
}

# 自动执行（如果直接运行脚本）
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    setup_links
fi
