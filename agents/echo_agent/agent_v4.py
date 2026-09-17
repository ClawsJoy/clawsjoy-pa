#!/usr/bin/env python3
"""EchoAgent v1.0 - 把用户输入原样返回"""

from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent


class EchoAgentV4(BusinessAgent):
    """回声Agent：把用户输入原样返回"""

    name = "echo_agent_v4"
    description = "回声助手，原样返回用户输入"
    version = "1.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print(f"🔊 EchoAgent v{self.version}")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.9)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """
        原样返回用户输入
        """
        return {
            "response": user_input,
            "agent": self.name,
            "version": self.version,
        }
