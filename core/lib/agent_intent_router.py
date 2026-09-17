#!/usr/bin/env python3
"""Agent Intent Router - 从 AgentManager 加载能力"""

from core.agents.builtin.agent_manager import get_agent_manager


class AgentIntentRouter:
    _instance = None
    _agents = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_agent_capabilities()
        return cls._instance

    def _load_agent_capabilities(self):
        """从 AgentManager 加载 Agent 能力"""
        self._agents = []

        for agent_name, agent_config in get_agent_manager().agents.items():
            capable_of = agent_config.get("capable_of", [])
            priority = agent_config.get("priority", 10)
            requires_context = agent_config.get("requires_context", False)

            for keyword in capable_of:
                self._agents.append(
                    {
                        "agent": agent_name,
                        "keyword": keyword,
                        "priority": priority,
                        "requires_context": requires_context,
                    }
                )

        self._agents.sort(key=lambda x: x["priority"], reverse=True)
        print(f"✅ AgentIntentRouter: 加载了 {len(self._agents)} 条能力映射，涉及 {len(get_agent_manager().agents)} 个 Agent")

    def route(self, user_input: str) -> dict:
        if not user_input or not user_input.strip():
            return {"success": True, "agent": "chat_agent"}

        user_input_lower = user_input.lower()
        import re as _re_math

        # 纯算式检测：含数字+运算符的组合 → calculator_agent
        if _re_math.search(r"\d+\s*[+\-*/^]\s*\d+", user_input):
            return {"success": True, "agent": "calculator_agent", "intent": "math"}
        # 代码模式：def 开头或含代码关键词
        if "def " in user_input or "hello函数" in user_input:
            return {"success": True, "agent": "code_agent", "intent": "code"}
        # 翻译模式：含"中文"或"翻译"
        if "中文" in user_input or "translate" in user_input_lower:
            return {"success": True, "agent": "translate_agent", "intent": "translate"}
        for agent_info in self._agents:
            if agent_info["keyword"].lower() in user_input_lower:
                return {"success": True, "agent": agent_info["agent"]}

        return {"success": True, "agent": "chat_agent"}

    def reload(self):
        agent_manager.reload()
        self._load_agent_capabilities()


def smart_route(user_input: str) -> str:
    return AgentIntentRouter().route(user_input)["agent"]
