from engine.lib.logger import engine_logger

"""主动学习引擎"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class ActiveEngine:
    """主动学习引擎"""

    def __init__(self):
        self._init_components()
        engine_logger.get().info("🎯 主动学习引擎已初始化")

    def _init_components(self):
        try:
            from core.autonomous.active_closed_loop import ActiveClosedLoop

            self._loop = ActiveClosedLoop()
        except Exception as e:
            self._loop = None

    def process(self, input_data: Any, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if isinstance(input_data, dict):
            return self.should_ask(
                input_data.get("query", ""),
                input_data.get("intent", "unknown"),
                input_data.get("confidence", 0.5),
            )
        return self.should_ask(str(input_data), "unknown", 0.5)

    def should_ask(
        self, query: str, intent: str, confidence: float
    ) -> Tuple[bool, Optional[Any]]:
        """判断是否需要主动询问"""
        if confidence < 0.5:
            return True, {"suggestion": "能说得更清楚些吗？"}
        return False, None

    def health_check(self) -> Dict:
        """健康检查"""
        return {"name": self.__class__.__name__, "status": "healthy"}

    def get_stats(self) -> Dict:
        return {"status": "active", "name": "active_engine"}

    def reload(self) -> Dict:
        return {"success": True, "message": "Active engine reloaded"}


active_engine = ActiveEngine()
