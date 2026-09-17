#!/usr/bin/env python3
"""Feedback Handler - Feedback Handler 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from core.lib.config_helper import get_data_root


class FeedbackHandler:
    """反馈处理器 - 收集用户反馈并触发学习"""

    def __init__(self):
        self.feedback_file = Path(f"{get_data_root()}/feedback.json")
        self.feedback_list = []
        self._load()

    def _load(self):
        if self.feedback_file.exists():
            with open(self.feedback_file, "r") as f:
                self.feedback_list = json.load(f)

    def _save(self):
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.feedback_file, "w") as f:
            json.dump(self.feedback_list, f, indent=2, default=str)

    def collect(self, feedback: Dict) -> Dict:
        """收集反馈"""
        feedback_entry = {
            "id": f"fb_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "user_id": feedback.get("user_id", "anonymous"),
            "type": feedback.get("type", "general"),
            "content": feedback.get("content", ""),
            "context": feedback.get("context", {}),
            "processed": False,
        }

        self.feedback_list.append(feedback_entry)
        self._save()

        # 触发学习
        self._trigger_learning(feedback_entry)

        return {"success": True, "id": feedback_entry["id"]}

    def _trigger_learning(self, feedback: Dict):
        """触发学习机制"""
        try:
            from core.lib.learning_hooks import learning_hooks

            if feedback.get("type") == "helpful":
                learning_hooks.stats["user_satisfaction"].append(
                    {"feedback": "positive", "timestamp": feedback["timestamp"]}
                )
                learning_hooks._save_stats()
                print(f"📚 从反馈中学习: 正面反馈")
            elif feedback.get("type") == "unhelpful":
                learning_hooks.stats["user_satisfaction"].append(
                    {"feedback": "negative", "timestamp": feedback["timestamp"]}
                )
                learning_hooks._save_stats()
                print(f"📚 从反馈中学习: 需要改进")
        except Exception as e:
            print(f"⚠️ 学习触发失败: {e}")

    def get_stats(self) -> Dict:
        """获取反馈统计"""
        total = len(self.feedback_list)
        helpful = sum(1 for f in self.feedback_list if f.get("type") == "helpful")
        unhelpful = sum(1 for f in self.feedback_list if f.get("type") == "unhelpful")

        return {
            "total": total,
            "helpful": helpful,
            "unhelpful": unhelpful,
            "satisfaction_rate": helpful / total if total > 0 else 0,
        }

    def _trigger_learning_with_coordinator(self, feedback: Dict):
        """使用学习协调器触发学习"""
        try:
            from core.learner.self_learning_coordinator import SelfLearningCoordinator

            coordinator = SelfLearningCoordinator()
            scenario = {
                "type": "feedback_improvement",
                "input": f"改进技能表现: {feedback.get('comment', '提高质量')}",
                "expected": "技能改进",
            }
            coordinator.learn_from_scenario(scenario)
            print(f"   📚 学习协调器已触发: {feedback.get('skill_id', 'unknown')}")
        except Exception as e:
            print(f"   ⚠️ 学习协调器触发失败: {e}")


feedback_handler = FeedbackHandler()
