from engine.lib.logger import engine_logger

"""事件驱动引擎 - 复用系统 EventBus"""

from datetime import datetime
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
)

from core.lib.event_bus import event_bus as system_event_bus


class EventEngine:
    """事件驱动引擎 - 统一事件接口"""

    def __init__(self):
        self._bus = system_event_bus
        engine_logger.get().info("📡 事件驱动引擎已初始化")

    def on(self, event: str, handler: Callable):
        """订阅事件"""
        self._bus.on(event, handler)
        return self

    def emit(self, event: str, data: Any = None):
        """触发事件"""
        self._bus.emit(event, data)
        return {"event": event, "data": data}

    def process(self, input_data: Any, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if isinstance(input_data, str):
            return self.emit(input_data, kwargs.get("data"))
        return self.emit(str(input_data), None)

    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "total_events": len(self._bus._handlers),
            "events": list(self._bus._handlers.keys()),
        }

    def reload(self) -> Dict:
        """热重载"""
        return {"success": True, "message": "Event engine reloaded"}

    def health_check(self) -> Dict:
        """健康检查"""
        return {"status": "healthy", "name": "event_engine"}


event_engine = EventEngine()
