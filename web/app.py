#!/usr/bin/env python3
"""ClawsJoy Web 主入口"""

import streamlit as st

st.set_page_config(page_title="ClawsJoy AI Studio", page_icon="🤖", layout="wide")

# 页面导航
st.sidebar.title("🤖 ClawsJoy AI Studio")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "选择功能",
    ["💬 Chat Agent", "💻 Code Agent", "🎨 Vision Agent", "📊 监控面板"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 提示\n\n"
    "- Chat: 支持语音输入和训练\n"
    "- Code: AI代码审查和优化\n"
    "- Vision: 工作流式图像生成"
)

# 加载对应页面
if page == "💬 Chat Agent":
    exec(open("web/chat_interface.py").read())
elif page == "💻 Code Agent":
    exec(open("web/code_interface.py").read())
elif page == "🎨 Vision Agent":
    exec(open("web/vision_interface.py").read())
else:
    exec(open("web/upgrade_dashboard_enhanced.py").read())
