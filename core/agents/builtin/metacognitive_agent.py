#!/usr/bin/env python3
"""Metacognitive Agent - Metacognitive Agent 模块

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

#!/usr/bin/env python3
"""元认知 Agent - 能反思自己的回答质量"""

import json
import re
from datetime import datetime
from pathlib import Path

from core.lib.config_manager import config_manager


class MetacognitiveAgent:
    """具有自我反思能力的 Agent"""

    def __init__(self):
        self.reflection_log = Path(f"{get_data_root()}/metacognition/reflections.json")
        self.reflection_log.parent.mkdir(parents=True, exist_ok=True)
        self._load_reflections()

    def _load_reflections(self):
        if self.reflection_log.exists():
            with open(self.reflection_log, "r") as f:
                self.reflections = json.load(f)
        else:
            self.reflections = []

    def reflect_on_response(
        self, user_input: str, response: str, user_feedback: str = None
    ):
        """反思自己的回答"""
        reflection = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input[:100],
            "response": response[:100],
            "feedback": user_feedback,
            "self_assessment": self._assess_response(response),
            "improvement": self._suggest_improvement(response),
        }
        self.reflections.append(reflection)
        self._save()
        return reflection

    def _assess_response(self, response: str) -> str:
        """自我评估回答质量"""
        if len(response) < 20:
            return "too_short"
        if "?" in response and "不知道" in response:
            return "unhelpful"
        if "你好" in response and len(response) > 50:
            return "verbose"
        return "good"

    def _suggest_improvement(self, response: str) -> str:
        """建议改进"""
        if self._assess_response(response) == "too_short":
            return "应该提供更详细的回答"
        if self._assess_response(response) == "unhelpful":
            return "应该尝试理解用户真实需求"
        return "保持当前风格"

    def _save(self):
        with open(self.reflection_log, "w") as f:
            json.dump(self.reflections[-100:], f, indent=2, ensure_ascii=False)

    def get_insights(self) -> dict:
        """获取反思洞察"""
        if not self.reflections:
            return {"message": "暂无反思记录"}

        good = sum(1 for r in self.reflections if r["self_assessment"] == "good")
        total = len(self.reflections)

        return {
            "total_reflections": total,
            "good_rate": round(good / total * 100, 1),
            "recent_improvements": [r["improvement"] for r in self.reflections[-5:]],
        }


if __name__ == "__main__":
    agent = MetacognitiveAgent()

    # 测试反思
    reflection = agent.reflect_on_response(
        "ClawsJoy 有什么功能？", "ClawsJoy 是一个智能系统", "不够详细"
    )
    print(f"反思结果: {reflection['self_assessment']}")
    print(f"改进建议: {reflection['improvement']}")
    print(f"\n洞察: {agent.get_insights()}")
