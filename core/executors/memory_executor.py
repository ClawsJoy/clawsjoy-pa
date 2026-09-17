#!/usr/bin/env python3
"""Memory Executor - Memory Executor 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from core.lib.memory import memory


class MemoryExecutor:
    """记忆执行器"""

    name = "memory_executor"

    def execute(self, goal: str, params: dict = None) -> dict:
        """执行记忆操作"""
        user_id = params.get("user_id", "default") if params else "default"

        # 记忆存储
        if "记住" in goal:
            content = goal.replace("记住", "").strip()
            if content:
                memory.remember(content, category="user_memory", user_id=user_id)
                return {
                    "success": True,
                    "message": f"已记住: {content}",
                    "source": "memory",
                }

        # 记忆回忆
        if "回忆" in goal or "还记得" in goal:
            query = goal.replace("回忆", "").replace("还记得", "").strip()
            if query:
                results = memory.recall(query, user_id=user_id, n=3)
                if results:
                    return {"success": True, "memories": results, "source": "memory"}
                else:
                    return {
                        "success": True,
                        "message": "没有找到相关记忆",
                        "source": "memory",
                    }

        return {"success": False, "error": "无法识别记忆操作"}


memory_executor = MemoryExecutor()
