#!/usr/bin/env python3
"""Agent Health - Agent Health 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from datetime import datetime
from typing import Dict, List


class AgentHealthCheck:
    """Agent 健康检查 - 简化版"""

    def __init__(self):
        self.health_history: Dict[str, List[Dict]] = {}

        # 内置 Agent 列表
        self.builtin_agents = [
            "orchestrator",
            "decision_agent",
            "executor_agent",
            "analysis_agent",
            "chat_agent",
            "code_agent",
            "collaboration_agent",
            "memory_agent",
            "security_agent",
            "video_agent",
            "youtube_agent",
            "translate_agent",
            "dialect_agent",
            "collector_agent",
            "hermes_agent",
            "analyst_agent",
            "copywriter_agent",
            "frontend_agent",
            "life_cycle_agent",
            "memory_manager",
            "do_anything",
            "test_agent_001",
            "inheritance_test_agent",
        ]

    def check_agent(self, agent_id: str) -> Dict:
        """检查单个 Agent 健康状态"""
        # 所有内置 Agent 默认为健康
        if agent_id in self.builtin_agents:
            status = "healthy"
        else:
            status = "unknown"

        # 记录历史
        if agent_id not in self.health_history:
            self.health_history[agent_id] = []
        self.health_history[agent_id].append(
            {"timestamp": datetime.now().isoformat(), "status": status}
        )
        self.health_history[agent_id] = self.health_history[agent_id][-10:]

        return {
            "agent": agent_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        }

    def check_all(self) -> Dict:
        """检查所有 Agent"""
        results = {}
        for agent_id in self.builtin_agents:
            results[agent_id] = self.check_agent(agent_id)
        return results

    def get_summary(self) -> Dict:
        """获取健康摘要"""
        results = self.check_all()
        healthy = sum(1 for r in results.values() if r.get("status") == "healthy")
        unhealthy_agents = [
            aid for aid, r in results.items() if r.get("status") != "healthy"
        ]
        return {
            "total": len(results),
            "healthy": healthy,
            "unhealthy": len(results) - healthy,
            "unhealthy_agents": unhealthy_agents,
            "details": results,
        }


# 全局实例
agent_health = AgentHealthCheck()
