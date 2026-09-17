#!/usr/bin/env python3
"""Agent Communication - Agent Communication 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""Agent 通信模块 - Agent 间消息传递"""

import json
import uuid
import threading
from collections import deque
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    ERROR = "error"
    BROADCAST = "broadcast"


class MessagePriority(Enum):
    HIGH = 0
    NORMAL = 1
    LOW = 2


class Message:
    """消息实体"""

    def __init__(
        self,
        msg_type: MessageType,
        from_agent: str,
        to_agent: str,
        payload: Dict = None,
        priority: MessagePriority = MessagePriority.NORMAL,
    ):
        self.id = str(uuid.uuid4())
        self.type = msg_type
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.payload = payload or {}
        self.priority = priority
        self.timestamp = datetime.now().isoformat()
        self.response = None
        self.status = "pending"

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "from": self.from_agent,
            "to": self.to_agent,
            "payload": self.payload,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "status": self.status,
        }


class AgentCommunication:
    """Agent 通信中心"""

    def __init__(self, max_history=100):
        self.message_history: deque = deque(maxlen=max_history)
        self.pending_responses: Dict[str, Message] = {}
        self.subscribers: Dict[str, List[str]] = {}  # event_type -> [agent_ids]
        self._lock = threading.Lock()
        self._message_queue = []
        self._subscribers = {}
        self._active_agents = {}      # 添加这一行
        self._pending_tasks = {}      # 添加这一行

    def send(
        self,
        from_agent: str,
        to_agent: str,
        payload: Dict,
        msg_type: MessageType = MessageType.REQUEST,
    ) -> str:
        """发送消息"""
        msg = Message(msg_type, from_agent, to_agent, payload)
        self.message_history.append(msg)

        if msg_type == MessageType.REQUEST:
            self.pending_responses[msg.id] = msg

        print(f"📨 {from_agent} -> {to_agent}: {payload.get('action', 'unknown')}")
        return msg.id

    def publish(self, event_type: str, data: Dict[str, Any]):
        """发布事件"""
        with self._lock:
            message = {
                "type": event_type,
                "data": data,
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
            self._message_queue.append(message)
            
            # 通知订阅者
            for agent in self._subscribers.get(event_type, []):
                print(f"📢 事件 {event_type} -> {agent}")

    def send_broadcast(self, from_agent: str, event_type: str, payload: Dict):
        """广播消息"""
        msg = Message(MessageType.BROADCAST, from_agent, "all", payload)
        msg.payload["event_type"] = event_type
        self.message_history.append(msg)
        print(
            f"📢 {from_agent} 广播 [{event_type}]: {payload.get('action', 'unknown')}"
        )
        return msg.id

    def respond(self, request_id: str, response_payload: Dict, success: bool = True):
        """响应请求"""
        if request_id not in self.pending_responses:
            return False

        req = self.pending_responses[request_id]
        resp = Message(MessageType.RESPONSE, "system", req.from_agent, response_payload)
        resp.status = "success" if success else "failed"

        req.response = resp
        req.status = "completed"

        self.message_history.append(resp)
        del self.pending_responses[request_id]

        print(f"📨 响应 -> {req.from_agent}: {response_payload.get('result', 'ok')}")
        return True

    def get_messages(self, agent_id: str = None, limit: int = 20) -> List[Dict]:
        """获取消息历史"""
        if agent_id:
            return [
                m.to_dict()
                for m in self.message_history
                if m.to_agent == agent_id or m.from_agent == agent_id
            ][-limit:]
        return [m.to_dict() for m in self.message_history][-limit:]

    def get_pending_requests(self, agent_id: str = None) -> List[Dict]:
        """获取待处理的请求"""
        pending = []
        for msg in self.pending_responses.values():
            if agent_id is None or msg.to_agent == agent_id:
                pending.append(msg.to_dict())
        return pending

    def subscribe(self, agent_id: str, event_type: str):
        """订阅事件"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        if agent_id not in self.subscribers[event_type]:
            self.subscribers[event_type].append(agent_id)

    def unsubscribe(self, agent_id: str, event_type: str):
        """取消订阅"""
        if event_type in self.subscribers and agent_id in self.subscribers[event_type]:
            self.subscribers[event_type].remove(agent_id)

    def emit_event(self, event_type: str, payload: Dict, from_agent: str = "system"):
        """发送事件给订阅者"""
        if event_type not in self.subscribers:
            return

        for agent_id in self.subscribers[event_type]:
            self.send(
                from_agent,
                agent_id,
                {**payload, "event_type": event_type},
                MessageType.EVENT,
            )

    def get_stats(self) -> Dict:
        """获取通信统计"""
        return {
            "total_messages": len(self.message_history),
            "pending_requests": len(self.pending_responses),
            "subscribers": {k: len(v) for k, v in self.subscribers.items()},
        }



# 全局实例
agent_comm = AgentCommunication()

# 兼容别名（用于主动服务）
agent_communication = agent_comm

# 标准化消息格式
class MessageFormat:
    """标准化 Agent 通信格式"""

    @staticmethod
    def request(
        target_agent: str, action: str, data: dict, request_id: str = None
    ) -> dict:
        """构建请求消息"""
        import uuid

        return {
            "type": "request",
            "id": request_id or str(uuid.uuid4()),
            "from": "system",
            "to": target_agent,
            "action": action,
            "data": data,
            "timestamp": None,  # 会在发送时填充
        }

    @staticmethod
    def response(request_id: str, result: dict, success: bool = True) -> dict:
        """构建响应消息"""
        return {
            "type": "response",
            "id": request_id,
            "success": success,
            "data": result,
            "timestamp": None,
        }

    @staticmethod
    def broadcast(event: str, data: dict, from_agent: str = "system") -> dict:
        """构建广播消息"""
        return {
            "type": "broadcast",
            "event": event,
            "from": from_agent,
            "data": data,
            "timestamp": None,
        }


# 全局实例
message_format = MessageFormat()

__version__ = "1.1.0"
__version_date__ = "2026-05-19"
__version_author__ = "ClawsJoy"
__changelog__ = "修复 send_message 方法，添加广播和订阅功能"
