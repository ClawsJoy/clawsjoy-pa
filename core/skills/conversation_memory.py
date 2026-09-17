#!/usr/bin/env python3
"""Conversation Memory - Conversation Memory 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from collections import defaultdict
from typing import Dict, Optional


class SimpleMemory:
    """简单记忆（仅当前会话）"""

    _instance = None
    _data = defaultdict(dict)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def set(self, user_id: str, key: str, value: str):
        self._data[user_id][key] = value

    def get(self, user_id: str, key: str) -> Optional[str]:
        return self._data[user_id].get(key)

    def get_all(self, user_id: str) -> dict:
        return dict(self._data[user_id])


simple_memory = SimpleMemory()
