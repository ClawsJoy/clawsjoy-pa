#!/usr/bin/env python3
"""Event Bus - Event Bus 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from collections import defaultdict
from typing import Any, Callable, Dict, List


class EventBus:
    """事件总线 - 单例模式，支持灵活 handler 签名"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers: Dict[str, List[Callable]] = defaultdict(list)
        return cls._instance

    def on(self, event: str, handler: Callable) -> Dict:
        """订阅事件（避免重复订阅）"""
        if handler not in self._handlers[event]:
            self._handlers[event].append(handler)

    def subscribe(self, event: str, handler: Callable) -> Dict:
        """订阅事件（on 的别名）"""
        self.on(event, handler)

    def emit(self, event: str, data: Any = None) -> Dict:
        """触发事件 - 支持 0/1/2 参数的 handler"""
        for handler in self._handlers.get(event, []):
            try:
                handler(event, data)
            except TypeError:
                try:
                    handler(event)
                except TypeError:
                    try:
                        handler()
                    except TypeError:
                        pass

    def publish(self, event: str, data: Any = None) -> Dict:
        """发布事件（emit 的别名）"""
        self.emit(event, data)

    def off(self, event: str, handler: Callable = None) -> Dict:
        """取消订阅"""
        if handler is None:
            self._handlers[event] = []
        elif handler in self._handlers[event]:
            self._handlers[event].remove(handler)


# 全局单例
event_bus = EventBus()


class ConditionalEventBus(EventBus):
    """扩展事件总线 - 支持条件触发"""

    def __init__(self):
        super().__init__()
        self._conditions: Dict[str, Dict] = {}
        self._thresholds: Dict[str, Dict] = {}
        self._monitor_thread = None
        self._running = False

    def when(
        self,
        condition_name: str,
        check_func: Callable,
        trigger_event: str,
        trigger_data: Any = None,
        interval: int = 60,
    ):
        """注册条件触发 - 当 check_func() 返回 True 时触发事件"""
        self._conditions[condition_name] = {
            "check": check_func,
            "event": trigger_event,
            "data": trigger_data,
            "interval": interval,
            "last_check": 0,
        }
        print(f"📋 注册条件: {condition_name} -> 事件 {trigger_event}")

    def when_threshold(
        self,
        name: str,
        get_value: Callable,
        threshold: float,
        operator: str,
        trigger_event: str,
        interval: int = 30,
    ):
        """注册阈值触发 - 当值超过阈值时触发事件"""
        self._thresholds[name] = {
            "get": get_value,
            "threshold": threshold,
            "operator": operator,
            "event": trigger_event,
            "interval": interval,
            "last_check": 0,
            "last_value": None,
            "triggered": False,
        }
        print(f"📊 注册阈值: {name} ({operator} {threshold}) -> 事件 {trigger_event}")

    def start_monitoring(self):
        """启动条件监控"""
        self._running = True
        import threading

        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        print("🔍 条件监控已启动")

    def _monitor_loop(self):
        """监控循环"""
        import time

        while self._running:
            now = time.time()

            # 检查条件
            for name, cond in self._conditions.items():
                if now - cond["last_check"] >= cond["interval"]:
                    cond["last_check"] = now
                    try:
                        if cond["check"]():
                            self.emit(cond["event"], cond["data"])
                    except Exception as e:
                        print(f"⚠️ 条件 {name} 检查失败: {e}")

            # 检查阈值
            for name, th in self._thresholds.items():
                if now - th["last_check"] >= th["interval"]:
                    th["last_check"] = now
                    try:
                        current = th["get"]()
                        if th["operator"] == ">":
                            if current > th["threshold"] and not th["triggered"]:
                                self.emit(
                                    th["event"],
                                    {"value": current, "threshold": th["threshold"]},
                                )
                                th["triggered"] = True
                            elif current <= th["threshold"]:
                                th["triggered"] = False
                        elif th["operator"] == "<":
                            if current < th["threshold"] and not th["triggered"]:
                                self.emit(
                                    th["event"],
                                    {"value": current, "threshold": th["threshold"]},
                                )
                                th["triggered"] = True
                            elif current >= th["threshold"]:
                                th["triggered"] = False
                        th["last_value"] = current
                    except Exception as e:
                        print(f"⚠️ 阈值 {name} 检查失败: {e}")

            time.sleep(5)  # 每5秒检查一次


# 全局实例


# 条件事件总线实例
conditional_bus = ConditionalEventBus()
