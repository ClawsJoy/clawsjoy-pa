#!/usr/bin/env python3
"""统一的帮助信息生成器 - 基于统一LLM客户端"""

from typing import Dict, Any, List, Optional
from core.lib.llm_client import llm_client


class HelpGenerator:
    """帮助信息生成器 - 个性化 + 能力推荐"""

    def __init__(self, agent_name: str, agent_description: str,
                 capabilities: list, examples: List[str] = None):
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.capabilities = capabilities
        self.examples = examples or []

    def generate(self, user_input: str = None,
                 user_profile: Dict = None) -> str:
        """生成帮助信息"""
        if user_input:
            return self._llm_help(user_input, user_profile)
        return self._simple_help()

    def _llm_help(self, user_input: str, user_profile: Dict = None) -> str:
        """使用 LLM 生成个性化帮助"""

        # 构建上下文
        context_parts = []
        if user_profile:
            if user_profile.get("name"):
                context_parts.append(f"用户: {user_profile['name']}")
            if user_profile.get("level"):
                context_parts.append(f"等级: {user_profile['level']}")

        context_str = "\n".join(context_parts) if context_parts else ""

        # 能力列表
        caps_str = "、".join(self.capabilities[:8])
        if len(self.capabilities) > 8:
            caps_str += f"等共{len(self.capabilities)}项"

        # 示例
        examples_str = ""
        if self.examples:
            examples_str = "\n使用示例:\n" + "\n".join(
                f"  • {e}" for e in self.examples[:4]
            )

        prompt = f"""{context_str}
用户说: {user_input}

我是 {self.agent_name}，{self.agent_description}。
我能做: {caps_str}{examples_str}

请用简短友好的方式（2-3句话），告诉用户我能帮他做什么。
如果用户输入暗示了具体需求，优先回应那个需求。
不要使用列表或Markdown格式，用自然段落回答。"""

        try:
            result = llm_client.generate(
                prompt=prompt,
                model="qwen2.5:1.5b",
                temperature=0.7,
                max_tokens=120,
                timeout=10,
                task_type="help"
            )
            if result and len(result.strip()) > 5:
                return result.strip()
        except Exception:
            pass

        return self._simple_help()

    def _simple_help(self) -> str:
        """简洁帮助（降级方案）"""
        caps = "、".join(self.capabilities[:5])
        result = f"💡 我是 {self.agent_name}，可以帮你 {caps}"

        if self.examples:
            result += "\n\n试试对我说：\n" + "\n".join(
                f"  • {e}" for e in self.examples[:3]
            )

        result += "\n\n需要我做什么？"
        return result

    def generate_contextual_help(self, error_context: Dict = None) -> str:
        """根据错误上下文生成帮助"""
        if not error_context:
            return self._simple_help()

        error_type = error_context.get("type", "unknown")
        error_msg = error_context.get("message", "")
        last_input = error_context.get("last_input", "")

        prompt = f"""用户遇到问题了。

错误类型: {error_type}
错误信息: {error_msg}
用户最后输入: {last_input}

我是 {self.agent_name}，{self.agent_description}

请友好地告诉用户出了什么问题，并给出2个具体的解决建议。
2-3句话，不要用技术术语。"""

        try:
            result = llm_client.generate(
                prompt=prompt,
                model="qwen2.5:7b-instruct-q4_0-gpu",
                temperature=0.5,
                max_tokens=120,
                timeout=10,
                task_type="help"
            )
            if result and len(result.strip()) > 5:
                return result.strip()
        except Exception:
            pass

        return f"😅 出了点小问题（{error_type}），请稍后重试或换个方式描述你的需求。"


# 全局实例（需要在使用时初始化）
help_generator = None


def get_help_generator(agent_name: str, agent_description: str,
                       capabilities: list, examples: List[str] = None) -> HelpGenerator:
    """获取或创建帮助生成器实例"""
    return HelpGenerator(agent_name, agent_description, capabilities, examples)
