#!/usr/bin/env python3
"""Chat Agent - 对接后端语音服务"""

import base64
import json
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

st.set_page_config(page_title="ClawsJoy Chat - 智能对话", page_icon="💬", layout="wide")

# API配置
API_BASE = "http://localhost:5002/api/v5"

# 初始化
if "messages" not in st.session_state:
    st.session_state.messages = []
if "training_data" not in st.session_state:
    training_file = Path("data/training_data.json")
    if training_file.exists():
        with open(training_file, "r", encoding="utf-8") as f:
            st.session_state.training_data = json.load(f)
    else:
        st.session_state.training_data = []
if "audio_bytes" not in st.session_state:
    st.session_state.audio_bytes = None

# 侧边栏
with st.sidebar:
    st.title("🎯 聊天训练")
    st.markdown("---")

    # 语音设置
    st.subheader("🎤 语音设置")
    use_voice = st.checkbox("启用语音输入", value=True)
    voice_lang = st.selectbox("语音语言", ["zh-CN", "en-US", "ja-JP"])

    st.markdown("---")

    # 训练数据
    st.subheader("📝 训练数据")
    with st.form("training_form"):
        user_input = st.text_area("用户输入", height=80)
        expected_response = st.text_area("期望回复", height=80)
        submitted = st.form_submit_button("💾 保存")

        if submitted and user_input and expected_response:
            # 调用后端训练API
            try:
                resp = requests.post(
                    f"{API_BASE}/train",
                    json={"input": user_input, "output": expected_response},
                )
                if resp.status_code == 200:
                    st.success("训练数据已保存!")
                    st.session_state.training_data.append(
                        {"input": user_input, "output": expected_response}
                    )
            except Exception as e:
                st.error("保存失败")

    st.markdown("---")

    # 统计
    st.metric("训练样本", len(st.session_state.training_data))

    if st.button("🗑️ 清空对话"):
        st.session_state.messages = []
        st.rerun()

# 主界面
st.title("🤖 ClawsJoy 智能对话助手")

# 语音输入
if use_voice:
    audio_value = st.audio_input("🎤 点击录音")
    if audio_value:
        st.session_state.audio_bytes = audio_value.getvalue()

# 聊天历史
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        with st.chat_message("assistant"):
            st.write(msg["content"])
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👍", key=f"like_{msg['id']}"):
                    st.success("感谢反馈")
            with col2:
                if st.button("👎", key=f"dislike_{msg['id']}"):
                    st.warning("已记录")

# 输入处理
input_col1, input_col2 = st.columns([5, 1])
with input_col1:
    user_input = st.chat_input("输入消息...")

# 语音转文字
if st.session_state.audio_bytes and use_voice:
    with st.spinner("语音识别中..."):
        try:
            # 调用后端语音识别
            files = {"audio": st.session_state.audio_bytes}
            resp = requests.post(f"{API_BASE}/speech/to_text", files=files)
            if resp.status_code == 200:
                user_input = resp.json().get("text", "")
                st.info(f"识别结果: {user_input}")
            st.session_state.audio_bytes = None
        except Exception as e:
            st.error(f"语音识别失败: {e}")

if user_input:
    # 添加用户消息
    st.session_state.messages.append(
        {"role": "user", "content": user_input, "id": len(st.session_state.messages)}
    )

    with st.spinner("思考中..."):
        try:
            # 调用聊天API
            resp = requests.post(
                f"{API_BASE}/chat",
                json={
                    "message": user_input,
                    "user_id": "web_user",
                    "voice_enabled": use_voice,
                },
                timeout=30,
            )

            if resp.status_code == 200:
                response = resp.json().get("response", "无响应")
    
                # 如果启用语音，调用 TTS 端点生成语音
                if use_voice and response:
                    try:
                        tts_resp = requests.post(
                            "http://localhost:5002/v5/tts",
                            json={"text": response}
                        )
                        if tts_resp.status_code == 200:
                            audio_bytes = base64.b64decode(tts_resp.json()["audio"])
                            st.audio(audio_bytes, format="audio/mp3")
                    except Exception as e:
                        st.warning(f"语音播报失败: {e}")               
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response,
                        "id": len(st.session_state.messages),
                    }
                )
            else:
                st.error(f"API错误: {resp.status_code}")

            st.rerun()
        except Exception as e:
            st.error(f"错误: {e}")
