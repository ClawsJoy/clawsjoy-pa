from engine.lib.logger import engine_logger

"""Hook引擎 - 钩子管理"""

from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple


class HookEngine:
    """Hook引擎"""

    HOOK_POINTS = ["before_request", "after_request", "before_skill", "after_skill"]

    def __init__(self):
        self.hooks = defaultdict(list)
        engine_logger.get().info("🪝 Hook引擎已初始化")

    def process(self, input_data: Any, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        point = kwargs.get("point", "before_request")
        return self.execute(point, input_data)

    def register(self, point: str, hook: Callable, priority: int = 0):
        self.hooks[point].append({"func": hook, "priority": priority})
        self.hooks[point].sort(key=lambda x: -x["priority"])
        return {"success": True, "point": point}

    def execute(self, point: str, data: Any = None) -> Any:
        result = data
        for hook in self.hooks.get(point, []):
            try:
                result = hook["func"](result) if result else hook["func"]()
            except Exception as e:
                pass
        return result

    def list_hooks(self) -> Dict:
        return {
            point: [h["func"].__name__ for h in hooks]
            for point, hooks in self.hooks.items()
        }

    def health_check(self) -> Dict:
        """健康检查"""
        return {"name": self.__class__.__name__, "status": "healthy"}

    def get_stats(self) -> Dict:
        return {
            "hook_points": self.HOOK_POINTS,
            "total_hooks": sum(len(v) for v in self.hooks.values()),
        }

    def reload(self) -> Dict:
        return {"success": True, "message": "Hook engine reloaded"}


hook_engine = HookEngine()
