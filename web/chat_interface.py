import base64
import io
import json
from datetime import datetime

import requests
import streamlit as st
from pydub import AudioSegment
import os
import sys
_root = os.path.dirname(os.path.abspath(__file__))
while os.path.dirname(_root) != _root and not os.path.exists(os.path.join(_root, "gateway_endpoint.py")):
    _root = os.path.dirname(_root)
sys.path.append(_root)  # 向上找到含 cheap reader 的那层（出口层不 import core，深度无关）
from gateway_endpoint import gateway_base_url

# API配置
GATEWAY_URL = gateway_base_url() + ""

# 页面配置
st.set_page_config(page_title="ClawsJoy Chat - 智能对话", page_icon="💬", layout="wide")

# 初始化会话状态
if "messages" not in st.session_state:
    st.session_state.messages = []
if "training_data" not in st.session_state:
    st.session_state.training_data = []


# 音频处理函数
@st.cache_data(ttl=300)
def process_audio(audio_bytes):
    """将音频转换为Whisper兼容的WAV格式"""
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        audio = audio.set_frame_rate(16000).set_channels(1)
        buffer = io.BytesIO()
        audio.export(buffer, format="wav")
        return buffer.getvalue()
    except Exception as e:
        st.error(f"音频处理失败: {e}")
        return None


def speech_to_text(audio_bytes):
    """调用后端语音识别"""
    try:
        wav_bytes = process_audio(audio_bytes)
        if not wav_bytes:
            return ""

        files = {"audio": ("recording.wav", wav_bytes, "audio/wav")}
        response = requests.post(f"{GATEWAY_URL}/speech/to_text", files=files, timeout=15)

        if response.status_code == 200:
            result = response.json()
            text = result.get("text", "")
            if text:
                return text
            else:
                st.warning("未识别到语音内容")
                return ""
        else:
            st.error(f"识别服务异常: {response.status_code}")
            return ""
    except requests.exceptions.ConnectionError:
        st.error("语音识别服务未启动")
        return ""
    except Exception as e:
        st.error(f"语音识别失败: {e}")
        return ""


def get_tts_audio(text):
    """获取TTS音频数据"""
    try:
        response = requests.post(f"{GATEWAY_URL}/v5/tts", json={"text": text}, timeout=30)

        if response.status_code == 200:
            result = response.json()
            audio_b64 = result.get("audio", "")
            if audio_b64:
                audio_bytes = base64.b64decode(audio_b64)
                # 转换为WAV以确保浏览器兼容
                try:
                    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
                    buffer = io.BytesIO()
                    audio.export(buffer, format="wav")
                    return buffer.getvalue()
                except Exception:
                    return audio_bytes
        return None
    except Exception as e:
        return None


# 侧边栏 - 训练面板
with st.sidebar:
    st.title("🎯 聊天训练")
    st.markdown("---")

    st.subheader("📝 添加训练数据")
    with st.form("training_form"):
        user_input = st.text_area("用户输入", height=80)
        expected_response = st.text_area("期望回复", height=80)
        submitted = st.form_submit_button("💾 保存训练数据")

        if submitted and user_input and expected_response:
            st.session_state.training_data.append(
                {
                    "input": user_input,
                    "output": expected_response,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            st.success("训练数据已保存!")

    st.markdown("---")
    st.subheader("📊 训练统计")
    st.metric("训练样本数", len(st.session_state.training_data))

    if st.button("📤 导出训练数据"):
        json_str = json.dumps(st.session_state.training_data, ensure_ascii=False)
        st.download_button("下载", json_str, file_name="training_data.json")

    st.markdown("---")
    st.caption(f"会话ID: {hash(str(st.session_state))}")

# 主界面
st.title("🤖 ClawsJoy 智能对话助手")

# 输入区域：语音 + 文字
col1, col2 = st.columns([5, 1])
with col1:
    user_text = st.chat_input("输入您的消息...")
with col2:
    audio_input = st.audio_input("🎤")

# 处理语音输入
input_text = user_text
if audio_input is not None:
    with st.spinner("🎯 正在识别语音..."):
        recognized = speech_to_text(audio_input.getvalue())
        if recognized:
            st.success(f"✅ 识别结果: {recognized}")
            input_text = recognized

# 发送消息
if input_text:
    st.session_state.messages.append({"role": "user", "content": input_text})

    with st.spinner("🤔 AI思考中..."):
        try:
            response = requests.post(
                f"{GATEWAY_URL}/api/v5/wisdom/chat",
                json={
                    "message": input_text,
                    "messages": st.session_state.messages,
                    "training_data": st.session_state.training_data,
                },
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                reply = result.get("response", "抱歉，无法处理您的请求。")
                st.session_state.messages.append({"role": "assistant", "content": reply})

                # TTS自动播报（只在有新回复时）
                if "last_tts_text" not in st.session_state:
                    st.session_state.last_tts_text = ""

                if reply != st.session_state.last_tts_text:
                    st.session_state.last_tts_text = reply
                    with st.spinner("🔊 生成语音..."):
                        audio_data = get_tts_audio(reply)
                        if audio_data:
                            st.markdown(
                                f'<audio autoplay><source src="data:audio/wav;base64,{base64.b64encode(audio_data).decode()}" type="audio/wav"></audio>',
                                unsafe_allow_html=True,
                            )
            else:
                st.error(f"请求失败 (状态码: {response.status_code})")
        except requests.exceptions.ConnectionError:
            st.error("❌ 后端服务未启动，请先启动 Gateway")
        except Exception as e:
            st.error(f"发生错误: {e}")

# 显示聊天记录
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # 助手消息添加重播按钮
        if msg["role"] == "assistant":
            if st.button("🔊 重播", key=f"replay_{i}"):
                with st.spinner("生成语音..."):
                    audio_data = get_tts_audio(msg["content"])
                    if audio_data:
                        st.markdown(
                            f'<audio autoplay><source src="data:audio/wav;base64,{base64.b64encode(audio_data).decode()}" type="audio/wav"></audio>',
                            unsafe_allow_html=True,
                        )
