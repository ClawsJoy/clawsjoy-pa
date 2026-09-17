#!/usr/bin/env python3
"""Voice Butler - Voice Butler 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config

"""语音版私人管家 - 增强版（支持唤醒词、连续对话）"""

import json
import queue
import threading
from pathlib import Path
from typing import Dict, Optional

from core.agents.personal_butler_v2 import PersonalButlerV2
from core.lib.user_crypto import UserCrypto
from core.lib.voice_service import voice_service


class VoiceButler:
    """语音版私人管家 - 支持唤醒词、连续对话"""

    WAKE_WORDS = ["小管", "管家", "你好小管", "hey butler", "clawsjoy"]

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.butler = PersonalButlerV2(user_id)
        self.crypto = UserCrypto(user_id, self._get_user_key())
        self.is_listening = False
        self.is_activated = False  # 是否已唤醒
        self.audio_queue = queue.Queue()
        self._listener_thread = None
        self._conversation_context = []

    def _get_user_key(self) -> str:
        """获取用户密钥（实际应从用户输入或配置文件获取）"""
        key_file = Path(
            funified_config.get("paths.users_dir", f"{get_data_root()}/users/")
            + "/{self.user_id}/butler_v2/key.secret"
        )
        if key_file.exists():
            return key_file.read_text().strip()
        else:
            import secrets

            key = secrets.token_urlsafe(32)
            key_file.parent.mkdir(parents=True, exist_ok=True)
            key_file.write_text(key)
            return key

    def process_voice(self, audio_file: str) -> Dict:
        """处理语音输入"""
        # 1. 语音转文字
        text = voice_service.speech_to_text(audio_file)
        if not text:
            return {"success": False, "error": "语音识别失败"}

        print(f"🎤 识别: {text}")

        # 2. 检查唤醒词
        if not self.is_activated:
            for wake_word in self.WAKE_WORDS:
                if wake_word.lower() in text.lower():
                    self.is_activated = True
                    response = "我在，有什么可以帮您？"
                    return self._respond_with_voice(response)

            return {"success": True, "activated": False, "message": "等待唤醒"}

        # 3. 处理退出的情况
        if "退出" in text or "结束" in text or "bye" in text.lower():
            self.is_activated = False
            response = "好的，随时叫我"
            return self._respond_with_voice(response)

        # 4. 文字处理
        result = self.butler.process(text)

        # 5. 记录对话上下文
        self._conversation_context.append(
            {
                "user": text,
                "butler": result.get("response", ""),
                "timestamp": datetime.now().isoformat(),
            }
        )
        if len(self._conversation_context) > 50:
            self._conversation_context = self._conversation_context[-50:]

        # 6. 加密存储敏感对话
        if "密码" in text or "私密" in text or "secret" in text.lower():
            self.crypto.encrypt(
                self._conversation_context[-1], f"secret_{int(time.time())}"
            )

        # 7. 文字转语音
        return self._respond_with_voice(result.get("response", "收到"))

    def _respond_with_voice(self, text: str) -> Dict:
        """语音回复"""
        audio_out = voice_service.text_to_speech(text)
        result = {"success": True, "activated": self.is_activated, "response": text}
        if audio_out:
            result["audio"] = audio_out
        return result

    def start_listening(self):
        """开始持续监听"""
        from core.lib.microphone_listener import MicrophoneListener

        self.is_listening = True
        self.listener = MicrophoneListener(callback=self._on_audio_received)
        self.listener.start()
        print(f"🎤 语音管家已启动，说 '{self.WAKE_WORDS[0]}' 唤醒我")
        return {"success": True, "wake_words": self.WAKE_WORDS}

    def _on_audio_received(self, audio_file: str):
        """收到音频时的回调"""
        result = self.process_voice(audio_file)
        if result.get("activated") is False and result.get("response"):
            # 播放唤醒提示
            voice_service.text_to_speech(result["response"], play_immediately=True)

    def stop_listening(self):
        """停止监听"""
        self.is_listening = False
        if hasattr(self, "listener"):
            self.listener.stop()
        print("🎤 语音管家已停止")
        return {"success": True}

    def get_conversation_history(self, limit: int = 20) -> list:
        """获取对话历史"""
        return self._conversation_context[-limit:]

    def clear_conversation(self):
        """清空对话上下文"""
        self._conversation_context = []
        return {"success": True}


# 全局实例
voice_butler = VoiceButler()
