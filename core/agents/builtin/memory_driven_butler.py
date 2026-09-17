#!/usr/bin/env python3
"""Memory Driven Butler - Memory Driven Butler 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from typing import Any, Dict, Optional

from core.agents.base.smart_agent import SmartAgent


class MemoryDrivenButler(SmartAgent):
    """记忆驱动管家"""

    name = "memory_driven_butler"
    description = "基于记忆的管家服务"
    version = "1.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.memory: Dict[str, Any] = {}

    def remember(self, key: str, value: Any):
        """记住信息"""
        self.memory[key] = value

    def recall(self, key: str) -> Optional[Any]:
        """回忆信息"""
        return self.memory.get(key)

    def get_stats(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "memory_size": len(self.memory),
        }


memory_driven_butler = MemoryDrivenButler()
