#!/usr/bin/env python3
"""Suggestion Engine - Suggestion Engine 模块

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

"""建议引擎 - 生成智能建议"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class SuggestionEngine:
    """建议引擎 - 基于分析和学习生成建议"""

    def __init__(self):
        self.suggestions_file = Path(f"{get_data_root()}/suggestions.json")
        self.suggestions = []
        self._load()

    def _load(self):
        if self.suggestions_file.exists():
            with open(self.suggestions_file, "r") as f:
                self.suggestions = json.load(f)

    def _save(self):
        self.suggestions_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.suggestions_file, "w") as f:
            json.dump(self.suggestions, f, indent=2, default=str)

    def generate(self, context: Dict) -> List[Dict]:
        """根据上下文生成建议"""
        suggestions = []

        # 基于分析结果生成建议
        analysis = context.get("analysis", {})

        # 性能优化建议
        if analysis.get("slow_response", False):
            suggestions.append(
                {
                    "type": "performance",
                    "title": "响应速度优化",
                    "description": "检测到响应变慢，建议检查 LLM 服务状态",
                    "priority": "high",
                    "action": "检查 ollama 服务",
                }
            )

        # 技能使用建议
        skill_usage = context.get("skill_usage", {})
        if skill_usage.get("frequent_skills"):
            suggestions.append(
                {
                    "type": "skill",
                    "title": "常用技能推荐",
                    "description": f"您经常使用 {skill_usage['frequent_skills'][:3]} 技能",
                    "priority": "medium",
                    "action": "可将常用技能添加到快捷方式",
                }
            )

        # 学习建议
        if context.get("learning_opportunity", False):
            suggestions.append(
                {
                    "type": "learning",
                    "title": "学习新技能",
                    "description": "系统检测到新的使用模式，建议学习相关技能",
                    "priority": "low",
                    "action": "查看技能商店",
                }
            )

        return suggestions

    def add_suggestion(self, suggestion: Dict):
        """添加建议记录"""
        suggestion["timestamp"] = datetime.now().isoformat()
        self.suggestions.append(suggestion)
        self._save()

    def get_pending(self, limit: int = 10) -> List[Dict]:
        """获取待处理的建议"""
        pending = [s for s in self.suggestions if not s.get("resolved", False)]
        return pending[:limit]

    def mark_resolved(self, suggestion_id: str):
        """标记建议已处理"""
        for s in self.suggestions:
            if s.get("id") == suggestion_id:
                s["resolved"] = True
                s["resolved_at"] = datetime.now().isoformat()
                break
        self._save()


suggestion_engine = SuggestionEngine()
