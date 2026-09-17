#!/usr/bin/env python3
"""ClawsJoy Web 完整版 - 对接后端服务"""

import requests
import streamlit as st

# 检查后端服务
try:
    resp = requests.get("http://localhost:5002/api/v5/health", timeout=2)
    BACKEND_AVAILABLE = resp.status_code == 200
except Exception as e:
    BACKEND_AVAILABLE = False

st.set_page_config(page_title="ClawsJoy AI Studio", page_icon="🤖", layout="wide")

# 侧边栏
st.sidebar.title("🤖 ClawsJoy AI Studio")

if not BACKEND_AVAILABLE:
    st.sidebar.error("⚠️ 后端服务未启动")
    st.sidebar.info("请先启动: python3 agent_gateway_enhanced.py")

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "选择功能",
    ["💬 Chat Agent", "💻 Code Agent", "🎨 Vision Agent", "📊 监控面板"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.info(
    f"**后端状态**: {'✅ 已连接' if BACKEND_AVAILABLE else '❌ 未连接'}\n\n"
    "**功能说明**:\n"
    "- Chat: 支持语音输入和训练\n"
    "- Code: AI代码审查和优化\n"
    "- Vision: 文生图工作流"
)

st.sidebar.markdown("---")
st.sidebar.markdown("[🔧 Workbench V8](http://localhost:5002/workbench)")
st.sidebar.markdown("[🎭 数字人](http://localhost:7860)")
st.sidebar.markdown("[🐾 v5.1 门户](http://localhost:5002/v5.1)")
st.sidebar.markdown("[📖 工具箱](http://localhost:5002/web/clawsjoy_story.html)")
# 加载页面
if page == "💬 Chat Agent":
    exec(open("web/chat_interface.py").read())
elif page == "💻 Code Agent":
    exec(open("web/code_interface_backend.py").read())
elif page == "🎨 Vision Agent":
    exec(open("web/vision_interface.py").read())
else:
    exec(open("web/upgrade_dashboard_enhanced.py").read())
