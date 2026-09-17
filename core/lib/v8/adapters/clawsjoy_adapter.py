#!/usr/bin/env python3
"""ClawsJoy 内置 Agent 适配器"""

from . import BaseAdapter


class ClawsJoyAdapter(BaseAdapter):
    """包装 ClawsJoy 内置 Agent"""

    def __init__(self, agent_name: str = "chat_agent_v4", **kwargs):
        super().__init__(**kwargs)
        self.agent_name = agent_name

    def execute(self, prompt: str, system_prompt: str = "", history: list = None) -> dict:
        try:
            from core.agents.wisdom.wisdom_factory import wisdom_factory
            agent = wisdom_factory.get_agent(self.agent_name, "workbench")
            if agent is None:
                from core.lib.llm_client import llm_client
                # 收集完整响应
                content = ""
                for token in llm_client.generate_stream(
                    prompt=prompt, model=self.model or "qwen2.5:7b-instruct-q4_0-gpu",
                    task_type="chat", system_prompt=system_prompt
                ):
                    content += token
                return {"success": True, "content": content, "tokens": 0, "model": self.model or "ollama"}
            result = agent.process(prompt)
            return {
                "success": result.get("success", False),
                "content": result.get("response", ""),
                "tokens": result.get("tokens", 0),
                "model": "ollama",
            }
        except Exception as e:
            return {"success": False, "content": f"Agent错误: {e}", "tokens": 0, "model": "ollama"}
