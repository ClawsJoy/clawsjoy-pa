#!/usr/bin/env python3
"""Analyst Agent - Analyst Agent 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
from pathlib import Path
from typing import Dict, List

from core.agents.base.smart_agent import SmartAgent


class AnalystAgent(SmartAgent):
    name = "analyst_agent"
    description = "分析用户问题，给出学习建议"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print("📊 分析师 已上岗")

    def analyze_unknown_questions(self) -> Dict:
        """分析未知问题，找出需要学习的"""
        unknown_file = Path("data/unknown_questions.json")
        if not unknown_file.exists():
            return {"has_unknown": False, "suggestions": []}

        with open(unknown_file, "r") as f:
            unknown = json.load(f)

        # 找出问过3次以上的问题
        suggestions = []
        for q, count in unknown.items():
            if count >= 3:
                suggestions.append(
                    {
                        "question": q,
                        "frequency": count,
                        "priority": "high" if count >= 5 else "medium",
                        "suggestion": f"建议学习：{q}",
                    }
                )

        return {
            "has_unknown": len(suggestions) > 0,
            "suggestions": suggestions,
            "total_questions": len(unknown),
        }

    def process(self, user_input: str, context=None) -> Dict:
        return self.analyze_unknown_questions()
