#!/usr/bin/env python3
"""Memory Manager - Memory Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""Memory Manager Agent - 记忆管理助手"""

from agents.base_agent import BaseAgent

from core.lib.config_manager import config_manager
from core.lib.memory_simple import memory


class MemoryManagerAgent(SmartAgent):
    name = "memory_manager"
    description = "记忆管理助手 - 管理记忆系统"
    version = "2.0.0"
    type = "core"

    capabilities = [
        {
            "name": "memory_store",
            "description": "存储记忆",
            "skills": ["memory_enhanced", "auto_remember"],
            "examples": ["记住这个信息", "保存重要内容"],
        },
        {
            "name": "memory_recall",
            "description": "回忆记忆",
            "skills": ["memory_query", "memory_enhanced"],
            "examples": ["查询之前的记录", "搜索记忆"],
        },
        {
            "name": "vector_search",
            "description": "向量语义搜索",
            "skills": ["memory_query"],
            "examples": ["语义搜索相关内容"],
        },
    ]

    personality = {
        "style": "professional",
        "language": "zh-CN",
        "tone": "precise",
        "greeting": "您好，我是记忆管理助手，帮您管理系统的记忆。",
    }

    def __init__(self):
        super().__init__(
            agent_id="memory_manager",
            config={
                "name": "记忆管理助手",
                "type": "core",
                "personality": "professional",
                "capabilities": self.capabilities,
            },
        )
        self.remember("Memory Manager Agent 已启动", shared=True)

    def execute(self, params):
        action = params.get("action", "")

        if action == "recall":
            query = params.get("query", "")
            results = memory.recall(query, n=5)
            return {"success": True, "results": results}
        elif action == "stats":
            return {"success": True, "stats": memory.get_stats()}

        return {"success": False, "error": f"未知操作: {action}"}


# memory_manager = MemoryManagerAgent()  # 注释：改为按需创建
