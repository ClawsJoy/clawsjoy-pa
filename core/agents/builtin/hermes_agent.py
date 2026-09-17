#!/usr/bin/env python3
"""Hermes Agent - Hermes Agent 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from typing import Dict, Optional

from core.agents.base.smart_agent import SmartAgent


class HermesAgent(SmartAgent):
    """消息传递 Agent"""

    name = "hermes_agent"
    description = "消息传递和通信"
    version = "1.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)

    def send_message(self, to: str, message: str) -> Dict:
        """发送消息"""
        return {"to": to, "message": message[:50], "status": "sent"}

    def get_stats(self) -> Dict:
        return {"name": self.name, "version": self.version}


# hermes_agent = HermesAgent()  # 注释：改为按需创建
