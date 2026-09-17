"""个性化推荐引擎"""

from collections import defaultdict
from typing import Any, Dict, List

from engine.lib.logger import engine_logger


class RecommendEngine:
    """个性化推荐引擎"""

    def __init__(self):
        self.user_preferences = defaultdict(lambda: defaultdict(int))
        engine_logger.get().info("🎯 推荐引擎已初始化")

    def process(self, input_data: Any = None, **kwargs) -> Any:
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, dict):
            if "record" in input_data:
                return self.record_interaction(**input_data.get("record", {}))
            return self.get_recommendations(input_data.get("user_id", "default"))
        return self.get_recommendations(str(input_data))

    def record_interaction(
        self, user_id: str, item_type: str, item_id: str, positive: bool = True
    ) -> Dict:
        self.user_preferences[user_id][item_type] += 1 if positive else -1
        return {"recorded": True}

    def get_recommendations(self, user_id: str, top_k: int = 5) -> List[Dict]:
        prefs = self.user_preferences.get(user_id, {})
        sorted_prefs = sorted(prefs.items(), key=lambda x: -x[1])
        return [
            {"type": item_type, "score": score}
            for item_type, score in sorted_prefs[:top_k]
        ]

    def get_stats(self) -> Dict:
        return {"users": len(self.user_preferences), "status": "active"}

    def reload(self) -> Dict:
        self.user_preferences.clear()
        return {"success": True, "message": "Recommend engine reloaded"}

    def health_check(self) -> Dict:
        return {"name": "recommend_engine", "status": "healthy"}


recommend_engine = RecommendEngine()
