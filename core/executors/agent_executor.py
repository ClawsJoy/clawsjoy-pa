#!/usr/bin/env python3
"""Agent Executor - Agent Executor 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from core.lib.agent_bus import get_bus


class AgentExecutor:
    """Agent 协作执行器"""

    name = "agent_executor"

    def __init__(self):
        self.bus = get_bus()

    def execute(self, goal: str, params: dict = None) -> dict:
        """执行 Agent 协作任务"""
        user_id = params.get("user_id", "default") if params else "default"

        # 识别需要的 Agent
        agents = self._identify_agents(goal)

        results = {}
        for agent in agents:
            # 发送任务到 Agent
            message_id = self.bus.publish(
                "brain",
                f"task.{agent}",
                {"goal": goal, "user_id": user_id, "source": "brain"},
            )
            results[agent] = {"status": "dispatched", "message_id": message_id}

        return {
            "success": True,
            "agents": agents,
            "results": results,
            "source": "agent_collaboration",
        }

    def _identify_agents(self, goal: str) -> list:
        """识别需要哪些 Agent"""
        agents = []

        if "代码" in goal or "编程" in goal:
            agents.append("code_agent")
        if "视频" in goal:
            agents.append("video_agent")
        if "分析" in goal:
            agents.append("analysis_agent")

        return agents if agents else ["chat_agent"]


agent_executor = AgentExecutor()
