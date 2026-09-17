#!/usr/bin/env python3
"""Code Agent - Continue风格代码编辑界面"""

import subprocess
import tempfile
from pathlib import Path

import requests
import streamlit as st

st.set_page_config(
    page_title="ClawsJoy Code - AI编程助手", page_icon="💻", layout="wide"
)

# 初始化
if "code_history" not in st.session_state:
    st.session_state.code_history = []
if "current_code" not in st.session_state:
    st.session_state.current_code = ""

# 侧边栏 - 历史记录
with st.sidebar:
    st.title("📚 代码历史")
    st.markdown("---")

    for i, item in enumerate(st.session_state.code_history[-10:]):
        with st.expander(f"版本 {len(st.session_state.code_history)-i}"):
            st.code(item.get("code", "")[:200])
            if st.button("恢复", key=f"restore_{i}"):
                st.session_state.current_code = item.get("code", "")
                st.rerun()

    st.markdown("---")
    st.subheader("⚙️ 设置")
    language = st.selectbox("语言", ["python", "javascript", "java", "go", "rust"])
    auto_save = st.checkbox("自动保存", True)

# 主界面
st.title("💻 ClawsJoy Code Assistant")
st.caption("AI驱动的代码编辑器 - 像Continue一样智能")

# 工具栏
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 4])
with col1:
    if st.button("▶️ 运行"):
        st.session_state.run_code = True
with col2:
    if st.button("🔍 审查"):
        st.session_state.review_code = True
with col3:
    if st.button("✨ 优化"):
        st.session_state.optimize_code = True
with col4:
    if st.button("💾 保存"):
        st.success("已保存")

# 代码编辑区
st.subheader("📝 代码编辑区")
code = st.text_area(
    "代码",
    value=st.session_state.current_code,
    height=400,
    key="code_editor",
    help="输入或粘贴代码，AI会帮你审查和优化",
)

# 运行结果区
if st.session_state.get("run_code"):
    st.subheader("▶️ 运行结果")
    if language == "python":
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            result = subprocess.run(["python3", f.name], capture_output=True, text=True)
            st.code(result.stdout if result.stdout else result.stderr)
    st.session_state.run_code = False

# AI审查
if st.session_state.get("review_code"):
    st.subheader("🔍 AI代码审查")
    with st.spinner("审查中..."):
        try:
            resp = requests.post(
                "http://localhost:5002/api/v5/code/review",
                json={"code": code, "language": language},
            )
            if resp.status_code == 200:
                review = resp.json().get("review", "无审查结果")
                st.markdown(review)
        except Exception as e:
            st.error("审查服务不可用")
    st.session_state.review_code = False

# AI优化
if st.session_state.get("optimize_code"):
    st.subheader("✨ AI优化建议")
    with st.spinner("优化中..."):
        try:
            resp = requests.post(
                "http://localhost:5002/api/v5/code/optimize",
                json={"code": code, "language": language},
            )
            if resp.status_code == 200:
                optimized = resp.json().get("optimized_code", code)
                st.code(optimized)
                if st.button("应用优化"):
                    st.session_state.current_code = optimized
                    st.rerun()
        except Exception as e:
            st.error("优化服务不可用")
    st.session_state.optimize_code = False

# 保存到历史
if code and code != st.session_state.current_code:
    st.session_state.current_code = code
    if auto_save:
        st.session_state.code_history.append(
            {
                "code": code,
                "language": language,
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }
        )
