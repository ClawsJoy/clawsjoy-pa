"""自主学习引擎"""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from engine.lib.logger import engine_logger


class SelfLearningEngine:
    """自主学习引擎"""

    def __init__(self):
        self.knowledge_base = defaultdict(
            lambda: {"count": 0, "success": 0, "last_seen": None}
        )
        engine_logger.get().info("📚 自主学习引擎已初始化")

    def process(self, input_data: Any = None, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, dict):
            return self.learn_from_feedback(**input_data)
        return {"error": "Invalid input"}

    def learn_from_feedback(
        self, query: str, action: str, success: bool, user_id: str = None
    ) -> Dict:
        key = f"{query}|{action}"
        self.knowledge_base[key]["count"] += 1
        if success:
            self.knowledge_base[key]["success"] += 1
        self.knowledge_base[key]["last_seen"] = datetime.now().isoformat()

        success_rate = (
            self.knowledge_base[key]["success"] / self.knowledge_base[key]["count"]
        )
        return {
            "learned": True,
            "success_rate": success_rate,
            "sample_count": self.knowledge_base[key]["count"],
        }

    def get_stats(self) -> Dict:
        total = len(self.knowledge_base)
        avg_success = (
            sum(
                d["success"] / d["count"]
                for d in self.knowledge_base.values()
                if d["count"] > 0
            )
            / total
            if total > 0
            else 0
        )
        return {
            "total_knowledge": total,
            "avg_success_rate": avg_success,
            "status": "active",
        }

    def reload(self) -> Dict:
        self.knowledge_base.clear()
        return {"success": True, "message": "Learning engine reloaded"}

    def health_check(self) -> Dict:
        return {"name": "learning_engine", "status": "healthy"}


self_learning_engine = SelfLearningEngine()
