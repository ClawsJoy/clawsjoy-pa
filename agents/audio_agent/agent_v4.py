#!/usr/bin/env python3
"""AudioAgent v4.2 - 精简稳定版（音频助手）"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import re
from pathlib import Path
from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent


class AudioAgentV4(BusinessAgent):
    """音频 Agent - 精简稳定版"""

    name = "audio_agent_v4"
    description = "智慧音频助手"
    version = "5.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.output_dir = Path(f"data/audio/{user_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"🎵 AudioAgent v{self.version} 启动")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.85)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        t = user_input.lower()
        
        if any(kw in t for kw in ["转文字", "音频转文字", "语音转文字"]):
            return self._transcribe_audio(user_input)
        
        if any(kw in t for kw in ["分析音频", "音频分析"]):
            return self._analyze_audio(user_input)
        
        return self._resp("🎵 输入「转文字 音频文件」或「分析音频 音频文件」")

    # ================================================================
    #  转文字
    # ================================================================

    def _transcribe_audio(self, user_input: str) -> Dict:
        content = re.sub(r'(转文字|音频转文字|语音转文字)', '', user_input).strip()
        if not content:
            content = "音频文件"
        
        result = self._call_llm(f"转录音频内容：{content}")
        return self._resp(f"📝 音频转文字\n\n{result or '转录完成'}") if result else self._resp(f"""
📝 音频转文字

音频：{content}

💡 可接入 Whisper API：
```bash
pip install openai-whisper
whisper {content} --model base
"""    )
    def _analyze_audio(self, user_input: str) -> Dict:
        content = re.sub(r'分析音频', '', user_input).strip()
        if not content:
            content = "音频内容"

        result = self._call_llm(f"分析音频：{content}（类型、内容、时长、音质、建议）")
        return self._resp(f"🎧 音频分析\n\n{result or '分析完成'}")
    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}


if __name__ == "__main__":
    agent = AudioAgentV4("test")
    print(agent.process("转文字 meeting.mp3")["response"])

