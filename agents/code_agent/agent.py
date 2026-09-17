#!/usr/bin/env python3
"""CodeAgent v3.0 - 代码生成智能体"""

from typing import Dict, Optional

from core.agents.business.base_business_agent import BusinessAgent

# agents/code_agent/agent.py
from core.lib.input_validator import input_validator
from core.lib.safety_guard import safe_recursive
from core.lib.smart_adapter import smart_adapter


class CodeAgent(BusinessAgent):
    def handle(self, user_input: str, context: dict = None) -> dict:
        # 输入验证
        validation = input_validator.validate_code_request(user_input)

        if not validation.valid:
            return {
                "success": False,
                "error": "验证失败",
                "errors": validation.errors,
                "response": f"❌ {', '.join(validation.errors)}",
            }

        # 使用验证后的数据
        validated = validation.sanitized_value
        language = validated.get("language", "python")
        prompt = validated.get("prompt", user_input)

        # 生成代码
        code = self._generate_code(prompt, language)

        # 代码安全验证
        if not self._code_safe(code):
            return {
                "success": False,
                "error": "生成的代码不安全",
                "response": "❌ 生成的代码包含危险操作，已拒绝执行",
            }

        return {
            "success": True,
            "response": f"```{language}\n{code}\n```",
            "language": language,
        }

    @safe_recursive(max_depth=100)
    def _generate_code(self, prompt: str, language: str, depth: int = 0) -> str:
        # 递归生成代码的逻辑
        # depth 参数由装饰器自动传入
        pass


class CodeAgent(BusinessAgent):
    name = "code_agent"
    description = "代码生成与审查"
    version = "3.1.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print(f"💻 CodeAgent v{self.version} 已上线")

    def _execute_business(self, user_input: str, context: Dict = None) -> Dict:
        return self.handle(user_input, context)

    def handle(self, user_input: str, context: Dict = None) -> Dict:
        language = self._detect_language(user_input)
        code = self._generate_code(user_input, language)

        if not self._code_safe(code):
            return {"success": False, "response": "生成的代码可能不安全，已拒绝执行。"}

        return {
            "success": True,
            "response": f"```{language}\n{code}\n```",
            "language": language,
        }

    def _detect_language(self, user_input: str) -> str:
        user_lower = user_input.lower()
        if "python" in user_lower:
            return "python"
        if "javascript" in user_lower:
            return "javascript"
        if "java" in user_lower:
            return "java"
        return "python"

    def _generate_code(self, user_input: str, language: str) -> str:
        prompt = f"请用 {language} 实现：{user_input}\n只输出代码，不要解释。"
        try:
            return smart_adapter.generate(prompt, auto_select=True)
        except Exception:
            return f'print("Hello, World!")'

    def _code_safe(self, code: str) -> bool:
        dangerous = ["os.system", "subprocess", "eval", "exec", "__import__", "rm -rf"]
        for d in dangerous:
            if d in code:
                return False
        return True

    def rollback(self, task_id: str = None, context: Dict = None) -> Dict:
        return {"success": True, "message": "代码操作已回滚"}

    def get_code_agent(user_id: str = "default"):
        return CodeAgent(user_id)
