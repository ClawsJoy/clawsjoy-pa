#!/usr/bin/env python3
"""Code Agent - 对接后端代码服务"""

import subprocess
import tempfile
from pathlib import Path

import requests
import streamlit as st

st.set_page_config(page_title="ClawsJoy Code - AI编程", page_icon="💻", layout="wide")

API_BASE = "http://localhost:5002/api/v5"

# 初始化
if "code_history" not in st.session_state:
    st.session_state.code_history = []
if "current_code" not in st.session_state:
    st.session_state.current_code = ""

# 侧边栏
with st.sidebar:
    st.title("📚 历史记录")
    language = st.selectbox("语言", ["python", "javascript", "java", "go", "rust"])

    for i, item in enumerate(st.session_state.code_history[-5:]):
        with st.expander(f"版本 {len(st.session_state.code_history)-i}"):
            st.code(item.get("code", "")[:100])
            if st.button("恢复", key=f"restore_{i}"):
                st.session_state.current_code = item.get("code", "")
                st.rerun()

# 主界面
st.title("💻 ClawsJoy Code Assistant")

# 工具栏
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("▶️ 运行", use_container_width=True):
        st.session_state.run_code = True
with col2:
    if st.button("🔍 审查", use_container_width=True):
        st.session_state.review_code = True
with col3:
    if st.button("✨ 优化", use_container_width=True):
        st.session_state.optimize_code = True
with col4:
    if st.button("💾 保存", use_container_width=True):
        if st.session_state.current_code:
            st.session_state.code_history.append(
                {
                    "code": st.session_state.current_code,
                    "language": language,
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                }
            )
            st.success("已保存")

# 代码编辑区
st.subheader("📝 代码")
code = st.text_area(
    "代码编辑器",
    value=st.session_state.current_code,
    height=400,
    key="code_editor",
    help="输入代码，AI会帮你审查和优化",
)
st.session_state.current_code = code

# 运行代码
if st.session_state.get("run_code"):
    st.subheader("▶️ 运行结果")
    if language == "python" and code:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            result = subprocess.run(["python3", f.name], capture_output=True, text=True)
            st.code(result.stdout if result.stdout else result.stderr)
    else:
        st.info(f"暂不支持运行 {language} 代码")
    st.session_state.run_code = False

# AI审查
if st.session_state.get("review_code") and code:
    st.subheader("🔍 AI代码审查")
    with st.spinner("审查中..."):
        try:
            resp = requests.post(
                f"{API_BASE}/code/review",
                json={"code": code, "language": language},
                timeout=30,
            )
            if resp.status_code == 200:
                st.markdown(resp.json().get("review", "无审查结果"))
            else:
                st.error("审查服务不可用")
        except Exception as e:
            st.error(f"错误: {e}")
    st.session_state.review_code = False

# AI优化
if st.session_state.get("optimize_code") and code:
    st.subheader("✨ AI优化建议")
    with st.spinner("优化中..."):
        try:
            resp = requests.post(
                f"{API_BASE}/code/optimize",
                json={"code": code, "language": language},
                timeout=30,
            )
            if resp.status_code == 200:
                optimized = resp.json().get("optimized_code", code)
                st.code(optimized)
                if st.button("应用优化"):
                    st.session_state.current_code = optimized
                    st.rerun()
        except Exception as e:
            st.error(f"错误: {e}")
    st.session_state.optimize_code = False
