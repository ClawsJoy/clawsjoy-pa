"""自学习主引擎 - 协调各学习器"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class SelfLearningEngine:
    """自学习主引擎"""

    def __init__(self):
        self.learning_log = Path("data/self_learning_log.json")
        self.enabled = True
        self._load_stats()
        print("🧬 自学习引擎已初始化")

    def _load_stats(self):
        if self.learning_log.exists():
            with open(self.learning_log, "r") as f:
                self.stats = json.load(f)
        else:
            self.stats = {
                "keywords_learned": 0,
                "vectors_synced": 0,
                "patterns_discovered": 0,
                "last_learning": None,
            }

    def _save_stats(self):
        self.stats["last_learning"] = datetime.now().isoformat()
        with open(self.learning_log, "w") as f:
            json.dump(self.stats, f, indent=2)

    def learn_from_interaction(
        self,
        user_id: str,
        query: str,
        intent: str,
        skill_used: str,
        success: bool,
        confidence: float,
    ):
        """从用户交互中学习"""
        if not self.enabled:
            return

        # 1. 学习关键词
        try:
            from engine.evolution.keyword_learner import keyword_learner

            keyword_learner.record_query(query, skill_used, success)
            if confidence < 0.6:
                # 低置信度，更积极学习
                keyword_learner.record_query(query, skill_used, True)
        except Exception as e:
            pass

        # 2. 发现新模式
        self._discover_pattern(user_id, query, intent, success)

    def _discover_pattern(self, user_id: str, query: str, intent: str, success: bool):
        """发现用户行为模式"""
        # 简化实现 - 可扩展
        pass

    def apply_learned(self, skill_matrix_engine):
        """应用学习成果到引擎"""
        applied = 0

        # 应用关键词
        try:
            from engine.evolution.keyword_learner import keyword_learner

            applied = keyword_learner.apply_to_engine(skill_matrix_engine)
            self.stats["keywords_learned"] += applied
        except Exception as e:
            pass

        self._save_stats()
        return applied

    def get_stats(self) -> Dict:
        """获取学习统计"""
        try:
            from engine.evolution.keyword_learner import keyword_learner

            suggestions = keyword_learner.get_suggestions()
        except Exception as e:
            suggestions = []

        return {
            "total_learned": self.stats["keywords_learned"],
            "pending_suggestions": len(suggestions),
            "vectors_synced": self.stats["vectors_synced"],
            "last_learning": self.stats["last_learning"],
        }


self_learning = SelfLearningEngine()
