"""记忆引擎 - 使用 SmartMemoryManager"""

from datetime import datetime
from typing import Any, Dict, Optional
from engine.lib.logger import engine_logger


class MemoryEngine:
    """记忆引擎 - 基于 SmartMemoryManager"""

    def __init__(self):
        self._managers = {}
        engine_logger.get().info("💾 记忆引擎已初始化")

    def _get_manager(self, user_id: str):
        """获取用户的记忆管理器"""
        if user_id not in self._managers:
            from core.butler.memory_manager import SmartMemoryManager
            self._managers[user_id] = SmartMemoryManager(user_id)
        return self._managers[user_id]

    def remember(self, key: str, value: Any, user_id: str = "default"):
        """存储记忆"""
        try:
            manager = self._get_manager(user_id)
            # 根据 key 类型选择存储方式
            if key.startswith("pref_"):
                manager.remember_preference(key[5:], value)
            else:
                manager.remember_fact(f"{key}: {value}", importance=5)
            return {"success": True, "key": key, "user_id": user_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def recall(self, key: str, user_id: str = "default") -> Optional[str]:
        """回忆记忆"""
        try:
            manager = self._get_manager(user_id)
            # 尝试作为偏好获取
            if key.startswith("pref_"):
                result = manager.recall_preference(key[5:])
                if result:
                    return result
            # 搜索上下文
            results = manager.recall_context(key, limit=1)
            if results:
                return results[0]
            return None
        except Exception as e:
            print(f"记忆回忆失败: {e}")
            return None

    def process(self, input_data: Any, **kwargs) -> Any:
        """统一处理接口"""
        if isinstance(input_data, dict):
            action = input_data.get("action", "recall")
            if action == "remember":
                return self.remember(
                    input_data.get("key"),
                    input_data.get("value"),
                    kwargs.get("user_id", "default"),
                )
            else:
                return self.recall(
                    input_data.get("key"), kwargs.get("user_id", "default")
                )
        return self.recall(str(input_data), kwargs.get("user_id", "default"))

    def health_check(self) -> Dict:
        return {"name": "memory_engine", "status": "healthy"}

    def get_stats(self) -> Dict:
        return {"status": "active", "name": "memory_engine"}

    def reload(self) -> Dict:
        return {"success": True, "message": "Memory engine reloaded"}


memory_engine = MemoryEngine()
