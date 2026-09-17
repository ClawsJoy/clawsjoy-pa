#!/usr/bin/env python3
"""Voice Service - Voice Service 模块

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

"""语音服务 - 生成语音文件"""
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


class VoiceService:
    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural"):
        self.voice = voice
        self.output_dir = Path(f"{get_data_root()}/voice_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def text_to_speech(self, text: str, output_file: str = None) -> Optional[str]:
        """文字转语音，返回文件路径"""
        if not output_file:
            output_file = str(self.output_dir / f"speech_{hash(text) % 10000}.mp3")

        cmd = [
            "edge-tts",
            "--text",
            text,
            "--voice",
            self.voice,
            "--write-media",
            output_file,
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                timeout=unified_config.get("timeouts.default", 30),
                check=True,
            )
            return output_file
        except Exception as e:
            print(f"TTS 失败: {e}")
            return None

    def speak(self, text: str):
        """生成语音并提示播放"""
        audio_file = self.text_to_speech(text)
        if audio_file:
            print(f"🔊 语音已生成: {audio_file}")
            print(f"   播放命令: ffplay {audio_file} -nodisp -autoexit")
            # 自动播放（如果有 ffplay）
            try:
                subprocess.run(
                    ["ffplay", "-nodisp", "-autoexit", audio_file],
                    capture_output=True,
                    timeout=10,
                )
            except Exception as e:
                pass


voice_service = VoiceService()

if __name__ == "__main__":
    voice_service.speak("你好，我是你的私人管家")
