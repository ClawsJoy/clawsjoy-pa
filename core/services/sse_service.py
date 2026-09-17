#!/usr/bin/env python3
"""Sse Service - Sse Service 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import asyncio
import json
import threading
from typing import Dict, Set

from flask import Response, stream_with_context


class SSEService:
    """SSE 主动推送服务"""

    def __init__(self):
        self.clients: Dict[str, Set] = {}  # user_id -> set of queue
        self._lock = threading.Lock()

    def subscribe(self, user_id: str, queue):
        """订阅消息"""
        with self._lock:
            if user_id not in self.clients:
                self.clients[user_id] = set()
            self.clients[user_id].add(queue)
        print(f"📡 SSE 订阅: {user_id}")

    def unsubscribe(self, user_id: str, queue):
        """取消订阅"""
        with self._lock:
            if user_id in self.clients:
                self.clients[user_id].discard(queue)

    def push(self, user_id: str, data: dict):
        """推送消息给用户"""
        with self._lock:
            if user_id not in self.clients:
                return
            for queue in self.clients[user_id]:
                queue.put(data)

    def create_stream(self, user_id: str):
        """创建 SSE 流"""
        import queue

        q = queue.Queue()
        self.subscribe(user_id, q)

        def generate():
            try:
                # 发送连接成功消息
                yield f"data: {json.dumps({'type': 'connected', 'user_id': user_id})}\n\n"
                while True:
                    data = q.get(timeout=30)
                    yield f"data: {json.dumps(data)}\n\n"
            except Exception as e:
                print(f"SSE 流错误: {e}")
            finally:
                self.unsubscribe(user_id, q)

        return Response(stream_with_context(generate()), mimetype="text/event-stream")


sse_service = SSEService()
