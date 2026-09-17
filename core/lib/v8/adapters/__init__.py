#!/usr/bin/env python3
"""适配器基类"""

from abc import ABC, abstractmethod
from typing import Dict, Optional


class BaseAdapter(ABC):
    """所有适配器的基类"""

    def __init__(self, api_key: str = "", model: str = "", **kwargs):
        self.api_key = api_key
        self.model = model
        self.config = kwargs

    @abstractmethod
    def execute(self, prompt: str, system_prompt: str = "", history: list = None) -> dict:
        """
        执行任务。
        返回: {"success": bool, "content": str, "tokens": int, "model": str}
        """
        pass

    def count_tokens(self, text: str) -> int:
        """粗略估算 token 数（1 token ≈ 0.75 字）"""
        return int(len(text) * 0.75)
