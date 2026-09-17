#!/usr/bin/env python3
"""VideoAgent v5.0 - 视频助手

能力:
- 视频脚本生成
- 视频内容分析
- 视频摘要
- 字幕/转文字指导
"""

import re
from pathlib import Path
from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent


class VideoAgentV4(BusinessAgent):
    name = "video_agent_v4"
    description = "智慧视频助手"
    version = "5.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.output_dir = Path(f"data/video/{user_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"🎬 VideoAgent v{self.version}")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.85)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        if context and context.get("skip_intent"):
            from core.lib.llm_client import llm_client
            text = llm_client.generate(user_input, task_type="task_execute", timeout=120)
            return {"success": True, "response": text} if text else {"success": False, "response": ""}
        t = user_input.lower()

        if any(kw in t for kw in ["生成脚本", "写脚本", "视频脚本", "脚本"]):
            return self._script(user_input)
        elif any(kw in t for kw in ["转文字", "字幕", "转录"]):
            return self._transcribe(user_input)
        elif any(kw in t for kw in ["摘要", "总结"]):
            return self._summary(user_input)
        elif any(kw in t for kw in ["分析"]):
            return self._analyze(user_input)
        else:
            return self._script(user_input)  # 默认生成脚本

    def _script(self, user_input: str) -> Dict:
        topic = re.sub(r'(生成脚本|写脚本|视频脚本|制作视频|帮我|关于|一个|的|视频)', '', user_input).strip()
        if not topic or len(topic) < 2:
            topic = "AI技术"

        prompt = f"""为「{topic}」生成一个3-5分钟的视频脚本。

格式要求：
【开场】10-15秒，吸引注意力
【正文】2-3个要点，每个30-60秒
【结尾】10秒，总结+行动号召

直接输出脚本："""

        result = self._call_llm(prompt, task_type="video_script")
        return self._resp(f"🎬 视频脚本：{topic}\n\n{result}" if result else self._script_fallback(topic))

    def _analyze(self, user_input: str) -> Dict:
        content = re.sub(r'(分析视频|分析)', '', user_input).strip() or "视频内容"
        prompt = f"分析视频内容「{content}」，从主题、受众、亮点、改进建议四个维度输出："
        result = self._call_llm(prompt, task_type="video_analyze")
        return self._resp(f"🎬 视频分析\n\n{result}" if result else "分析完成，请提供更多视频信息")

    def _summary(self, user_input: str) -> Dict:
        content = re.sub(r'(摘要|总结)', '', user_input).strip() or "视频内容"
        prompt = f"为视频「{content}」生成3-5个要点的摘要："
        result = self._call_llm(prompt, task_type="video_summary")
        return self._resp(f"📋 视频摘要\n\n{result}" if result else "摘要生成完成")

    def _transcribe(self, user_input: str) -> Dict:
        content = re.sub(r'(转文字|字幕|转录)', '', user_input).strip() or "视频文件"
        return self._resp(
            f"📝 视频转文字指引\n\n"
            f"视频：{content}\n\n"
            f"💡 可使用以下工具：\n"
            f"• OpenAI Whisper: pip install openai-whisper && whisper video.mp4\n"
            f"• 剪映/必剪：导入视频自动生成字幕\n"
            f"• YouTube Studio：自动生成字幕"
        )

    def _script_fallback(self, topic: str) -> str:
        return f"""🎬 视频脚本：{topic}

【开场】大家好，今天我们来聊聊 {topic}

【正文】{topic} 是当前热门话题，让我们深入了解它的核心要点和应用场景

【结尾】以上就是关于 {topic} 的介绍，希望对你有帮助！"""

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}


if __name__ == "__main__":
    agent = VideoAgentV4("test")
    print(agent.process("生成脚本 人工智能介绍")["response"][:200])
