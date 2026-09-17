#!/usr/bin/env python3
"""Agent Bus - Agent Bus 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""
Agent 消息总线 v2.0
支持发布/订阅 + 消息队列
"""

import json
import queue
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Message:
    """消息结构"""

    id: str
    sender: str
    topic: str
    content: Dict
    timestamp: str
    priority: int = 0

    def __lt__(self, other) -> Dict:
        """支持优先级队列比较"""
        return self.priority < other.priority

    def __le__(self, other) -> Dict:
        return self.priority <= other.priority

    def __gt__(self, other) -> Dict:
        return self.priority > other.priority

    def __ge__(self, other) -> Dict:
        return self.priority >= other.priority


class AgentBus:
    """Agent 消息总线 - 支持发布/订阅和消息队列"""

    def __init__(self) -> Dict:
        self.subscribers: Dict[str, List[str]] = {}
        self.message_queue = queue.PriorityQueue()
        self.message_history: List[Message] = []
        self.max_history = 1000
        self._listener_thread = None
        self._running = False
        self._handlers: Dict[str, List[callable]] = {}

    def _generate_id(self) -> str:
        """生成消息ID"""
        import uuid

        return str(uuid.uuid4())

    def publish(
        self, sender: str, topic: str, content: Dict, priority: int = 0
    ) -> Dict:
        """发布消息到主题"""
        message = Message(
            id=self._generate_id(),
            sender=sender,
            topic=topic,
            content=content,
            timestamp=datetime.now().isoformat(),
            priority=priority,
        )

        self.message_queue.put((priority, message))
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history :]

        if topic in self.subscribers:
            for subscriber in self.subscribers[topic]:
                self._notify(subscriber, message)

        print(f"📢 [{sender}] 发布 [{topic}]: {content}")
        return message.id

    def subscribe(self, agent_name: str, topic: str) -> Dict:
        """订阅主题"""
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        if agent_name not in self.subscribers[topic]:
            self.subscribers[topic].append(agent_name)
            print(f"📡 [{agent_name}] 订阅 [{topic}]")

    def unsubscribe(self, agent_name: str, topic: str) -> Dict:
        """取消订阅"""
        if topic in self.subscribers and agent_name in self.subscribers[topic]:
            self.subscribers[topic].remove(agent_name)
            print(f"📡 [{agent_name}] 取消订阅 [{topic}]")

    def register_handler(self, topic: str, handler: callable) -> Dict:
        """注册消息处理器"""
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append(handler)
        print(f"🔧 注册处理器: {handler.__name__} -> [{topic}]")

    def _notify(self, agent_name: str, message: Message) -> Dict:
        """通知订阅者"""
        if agent_name in self._handlers:
            for handler in self._handlers[agent_name]:
                try:
                    handler(message)
                except Exception as e:
                    print(f"❌ 处理器 {handler.__name__} 失败: {e}")

    def get_message(self, timeout: float = 0.1) -> Optional[Message]:
        """获取一条消息（非阻塞）"""
        try:
            priority, message = self.message_queue.get(timeout=timeout)
            return message
        except queue.Empty:
            return None

    def get_messages(self, limit: int = 10) -> List[Message]:
        """获取多条消息"""
        messages = []
        for _ in range(limit):
            msg = self.get_message()
            if msg:
                messages.append(msg)
            else:
                break
        return messages

    def get_history(self, topic: str = None, limit: int = 50) -> List[Dict]:
        """获取消息历史"""
        history = self.message_history
        if topic:
            history = [m for m in history if m.topic == topic]
        return [asdict(m) for m in history[-limit:]]

    def start_listener(self, callback: callable = None) -> Dict:
        """启动消息监听器（后台线程）"""
        if self._running:
            print("⚠️ 监听器已在运行")
            return

        self._running = True

        def _listen():
            print("📡 消息监听器已启动")
            while self._running:
                message = self.get_message(timeout=0.5)
                if message and callback:
                    try:
                        callback(message)
                    except Exception as e:
                        print(f"❌ 消息处理失败: {e}")

        self._listener_thread = threading.Thread(target=_listen, daemon=True)
        self._listener_thread.start()

    def stop_listener(self) -> Dict:
        """停止消息监听器"""
        self._running = False
        print("📡 消息监听器已停止")

    def get_status(self) -> Dict:
        """获取总线状态"""
        return {
            "topics": len(self.subscribers),
            "total_subscriptions": sum(len(v) for v in self.subscribers.values()),
            "queue_size": self.message_queue.qsize(),
            "history_size": len(self.message_history),
            "handlers": len(self._handlers),
            "subscribers": {t: s for t, s in self.subscribers.items()},
        }


# 全局单例
_bus_instance = None


def get_bus() -> AgentBus:
    """获取全局总线实例"""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = AgentBus()
    return _bus_instance
