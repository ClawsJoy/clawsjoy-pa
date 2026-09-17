"""事件触发机制 - 懒加载后的主动唤醒"""

import threading
import time
from enum import Enum
from typing import Callable, Dict, List


class EventType(Enum):
    AGENT_NEEDED = "agent_needed"
    SKILL_NEEDED = "skill_needed"
    MEMORY_NEEDED = "memory_needed"
    TASK_ARRIVED = "task_arrived"


class EventTrigger:
    """事件触发器 - 按需唤醒组件"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._pending_events: List[Dict] = []
        print("⚡ 事件触发器已启动")

    def on(self, event_type: EventType, handler: Callable):
        """注册事件处理器"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def emit(self, event_type: EventType, data: Dict = None):
        """触发事件"""
        print(f"⚡ 事件触发: {event_type.value}")
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    print(f"事件处理失败: {e}")
        else:
            self._pending_events.append({"type": event_type, "data": data})

    def process_pending(self):
        """处理待处理事件"""
        for event in self._pending_events:
            self.emit(event["type"], event["data"])
        self._pending_events.clear()


event_trigger = EventTrigger()
