"""技能自增量学习 - 从使用中自动学习"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from engine.lib.logger import engine_logger


class SkillIncrementalLearner:
    """技能自增量学习器"""

    def __init__(self):
        self.usage_stats = defaultdict(
            lambda: {"count": 0, "success": 0, "last_used": None}
        )
        self.learning_log = Path("data/skill_learning.json")
        self._load()
        engine_logger.get().info("🧠 技能自增量学习器已初始化")

    def _load(self):
        if self.learning_log.exists():
            with open(self.learning_log, "r") as f:
                data = json.load(f)
                self.usage_stats.update(data.get("usage_stats", {}))

    def _save(self):
        with open(self.learning_log, "w") as f:
            json.dump(
                {
                    "usage_stats": dict(self.usage_stats),
                    "updated_at": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

    def record_usage(self, skill_name: str, success: bool, latency_ms: float = 0):
        """记录技能使用"""
        self.usage_stats[skill_name]["count"] += 1
        if success:
            self.usage_stats[skill_name]["success"] += 1
        self.usage_stats[skill_name]["last_used"] = datetime.now().isoformat()
        self._save()

    def get_recommendations(self, top_k: int = 5) -> List[Dict]:
        """获取推荐技能"""
        recommendations = []
        for name, stats in self.usage_stats.items():
            if stats["count"] > 0:
                success_rate = stats["success"] / stats["count"]
                recommendations.append(
                    {
                        "skill": name,
                        "usage_count": stats["count"],
                        "success_rate": success_rate,
                        "score": stats["count"] * success_rate,
                    }
                )

        return sorted(recommendations, key=lambda x: -x["score"])[:top_k]

    def get_stats(self) -> Dict:
        return {
            "total_skills_used": len(self.usage_stats),
            "total_usage": sum(s["count"] for s in self.usage_stats.values()),
            "avg_success_rate": (
                sum(
                    s["success"] / s["count"]
                    for s in self.usage_stats.values()
                    if s["count"] > 0
                )
                / len(self.usage_stats)
                if self.usage_stats
                else 0
            ),
        }


skill_learner = SkillIncrementalLearner()
