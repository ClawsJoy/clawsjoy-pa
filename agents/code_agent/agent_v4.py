#!/usr/bin/env python3
"""CodeAgent v5.0 - 专注代码能力"""

import re
from typing import Dict, Optional, Tuple, List

from core.agents.business.business_agent import BusinessAgent


class CodeAgentV4(BusinessAgent):
    """代码助手 v5.0 - 只做代码相关"""

    name = "code_agent_v4"
    description = "智能代码助手"
    version = "5.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print(f"💻 CodeAgent v{self.version}")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.9)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        t = user_input.lower()

        if any(kw in t for kw in ["修复", "fix", "改错", "改正"]):
            return self._fix(user_input)
        elif any(kw in t for kw in ["解释", "说明", "explain", "这段代码"]):
            return self._explain(user_input)
        elif any(kw in t for kw in ["审查", "review", "检查", "分析代码"]):
            return self._review(user_input)
        else:
            return self._generate(user_input)

    def _generate(self, user_input: str) -> Dict:
        code = self._extract_code(user_input)
        if code:
            return self._resp(f"```python\n{code}\n```")

        prompt = f"""你是专业代码助手。根据需求生成代码，只输出代码和简短注释。

需求：{user_input}

要求：
- 代码完整可运行
- 包含必要的导入
- 关键逻辑加注释
- 只输出代码块"""

        result = self._call_llm(prompt, task_type="code_generate")
        return self._resp(result if result else "生成失败，请重试")

    def _fix(self, user_input: str) -> Dict:
        code = self._extract_code(user_input)
        if not code:
            return self._resp("请提供要修复的代码和错误信息。\n\n示例：修复代码\n```python\ndef sort(lst):\n    return lst.sort()\n```\n错误：sort()返回None")

        prompt = f"""修复以下代码的问题，只输出修复后的完整代码：

{code}

用户需求：{user_input[:200]}"""

        result = self._call_llm(prompt, task_type="code_fix")
        return self._resp(f"## 🔧 修复结果\n\n```python\n{result}\n```" if result else "修复失败")

    def _explain(self, user_input: str) -> Dict:
        code = self._extract_code(user_input)
        if not code:
            return self._resp("请提供要解释的代码")

        prompt = f"用通俗语言逐行解释这段代码，适合初学者：\n\n```\n{code[:1500]}\n```"
        result = self._call_llm(prompt, task_type="code_explain")
        return self._resp(f"## 📖 代码解释\n\n{result}" if result else "解释失败")

    def _review(self, user_input: str) -> Dict:
        code = self._extract_code(user_input)
        if not code:
            return self._resp("请提供要审查的代码")

        prompt = f"""审查以下代码，从正确性、性能、可读性、安全性四个维度给出建议：

```python
{code[:2000]}
输出格式：

代码审查
✅ 优点
⚠ 问题
💡 改进建议"""
        result = self._call_llm(prompt, task_type="code_review", max_tokens=1024)
        return self._resp(result if result else "审查失败")

    def _extract_code(self, text: str) -> Optional[str]:
        match = re.search(r'```(?:python)?\s*\n(.*?)```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}

if __name__ == "__main__":
    agent = CodeAgentV4("test")
    print(agent.process("写一个快速排序")["response"][:200])
