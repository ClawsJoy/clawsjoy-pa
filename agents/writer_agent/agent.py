#!/usr/bin/env python3
"""WriterAgent - 写作智能体"""

from typing import Dict, Optional

from core.agents.business.business_agent_v2 import BusinessAgentV2


class WriterAgent(BusinessAgentV2):
    name = "writer_agent"
    description = "写作助手"
    version = "3.3.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print(f"✍️ 作家 v{self.version} 已上岗")

    def _execute_business(self, user_input: str, context: dict = None) -> dict:
        """业务逻辑实现 - 必需"""
        return self.handle(user_input, context)

    def handle(self, user_input: str, context: dict = None) -> dict:
        """处理写作请求"""
        return {
            "success": True,
            "response": f"✍️ 收到写作请求: {user_input[:100]}",
            "agent": self.name,
            "user_id": self.user_id,
        }


def get_writer_agent(user_id: str = "default"):
    return WriterAgent(user_id)

    def rollback(self, task_id: str, context: dict = None) -> dict:
        """回滚写作操作"""
        # 删除生成的草稿文件
        import os

        draft_file = f"data/drafts/{task_id}.txt"
        if os.path.exists(draft_file):
            os.remove(draft_file)
            return {"success": True, "message": f"已删除草稿: {draft_file}"}
        return {"success": True, "message": "无需要回滚的内容"}
