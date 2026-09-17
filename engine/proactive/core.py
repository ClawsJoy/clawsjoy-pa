"""主动服务引擎"""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from engine.lib.logger import engine_logger


class ProactiveEngine:
    """主动服务引擎"""

    def __init__(self):
        self.user_patterns = defaultdict(list)
        engine_logger.get().info("🚀 主动服务引擎已初始化")

    def process(self, input_data: Any = None, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, dict):
            action = input_data.get("action", "suggest")
            if action == "record":
                return self.record_behavior(
                    input_data.get("user_id", "default"),
                    input_data.get("action_type", "unknown"),
                )
            return self.suggest_proactive_action(
                input_data.get("user_id", "default"), input_data.get("context", {})
            )
        return self.suggest_proactive_action(str(input_data), {})

    def record_behavior(self, user_id: str, action: str, context: Dict = None) -> Dict:
        self.user_patterns[user_id].append(
            {
                "action": action,
                "context": context or {},
                "timestamp": datetime.now().isoformat(),
            }
        )
        if len(self.user_patterns[user_id]) > 100:
            self.user_patterns[user_id] = self.user_patterns[user_id][-100:]
        return {"recorded": True}

    def suggest_proactive_action(self, user_id: str, current_context: Dict) -> Dict:
        """建议主动动作"""
        from datetime import datetime

        hour = datetime.now().hour
        if 6 <= hour <= 10:
            return {
                "action": "morning_greeting",
                "reason": "早晨问候",
                "priority": "medium",
            }
        elif 12 <= hour <= 14:
            return {
                "action": "lunch_reminder",
                "reason": "午餐提醒",
                "priority": "medium",
            }
        elif 18 <= hour <= 22:
            return {
                "action": "evening_summary",
                "reason": "晚间总结",
                "priority": "medium",
            }
        return {"action": "check_in", "reason": "日常关怀", "priority": "low"}

    def get_stats(self) -> Dict:
        return {"users_tracked": len(self.user_patterns), "status": "active"}

    def reload(self) -> Dict:
        self.user_patterns.clear()
        return {"success": True, "message": "Proactive engine reloaded"}

    def health_check(self) -> Dict:
        return {"name": "proactive_engine", "status": "healthy"}


proactive_engine = ProactiveEngine()
