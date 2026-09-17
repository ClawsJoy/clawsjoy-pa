#!/usr/bin/env python3
"""Orchestrator - 任务编排器"""

import sys

sys.path.insert(0, "/home/flybo/clawsjoy_v5")

from typing import Dict, Optional

from core.agents.business.business_agent_v2 import BusinessAgentV2
from core.orchestration.service import orchestration_service


class OrchestratorAgent(BusinessAgentV2):
    name = "orchestrator"
    description = "任务编排与分发"
    version = "6.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print(f"[Orchestrator] v{self.version} 初始化完成")

    def _execute_business(self, user_input: str, context: Dict = None) -> Dict:
        """业务逻辑 - 调用编排服务"""
        result = orchestration_service.execute(user_input, self.user_id)

        if not result.get("success"):
            return {"success": False, "response": "编排执行失败"}

        # 格式化响应
        responses = [
            r.get("response", "")
            for r in result.get("results", [])
            if r.get("response")
        ]

        return {
            "success": True,
            "response": "\n".join(responses) if responses else "任务完成",
            "results": result.get("results", []),
            "plan_id": result.get("plan_id"),
        }


def get_orchestrator(user_id: str = "default"):
    return OrchestratorAgent(user_id)
