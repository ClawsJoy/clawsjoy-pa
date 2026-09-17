#!/usr/bin/env python3
"""CalculatorAgent v4.2 - 精简稳定版（科学计算器）"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import re
import math
from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent


class CalculatorAgentV4(BusinessAgent):
    """科学计算器 - 精简稳定版"""

    name = "calculator_agent_v4"
    description = "科学计算助手"
    version = "5.0.0"

    MATH_FUNCTIONS = {
        'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
        'asin': math.asin, 'acos': math.acos, 'atan': math.atan,
        'log': math.log, 'log10': math.log10, 'log2': math.log2,
        'exp': math.exp, 'abs': abs,
        'floor': math.floor, 'ceil': math.ceil, 'round': round,
        'factorial': math.factorial,
    }

    CONSTANTS = {'pi': math.pi, 'e': math.e, 'tau': math.tau}

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print(f"🔢 CalculatorAgent v{self.version} 启动")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.85)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        # 优先从 context 获取已提取的表达式
        extracted = context.get("extracted", {}) if context else {}
        expression = extracted.get("expression", "") or self._extract_expression(user_input)
        if not expression:
            return self._resp(self._help())
        
        result = self._calculate(expression)
        return self._resp(result)

    # ================================================================
    #  计算核心
    # ================================================================

    def _calculate(self, expression: str) -> str:
        # 安全检查：表达式不能太长，不能包含危险字符
        if len(expression) > 200:
            return "❌ 表达式过长"
        if any(kw in expression.lower() for kw in ['__', 'import', 'exec', 'open', 'file']):
            return "❌ 不安全的表达式"
        try:
            expr = self._preprocess(expression)
            safe_dict = {
                "__builtins__": {},
                "abs": abs, "round": round, "int": int, "float": float,
                "math": math,
                **self.MATH_FUNCTIONS,
                **self.CONSTANTS,
            }
            result = eval(expr, safe_dict, {})
            
            if isinstance(result, float):
                if result.is_integer():
                    result = int(result)
                else:
                    result = round(result, 8)
            
            return f"🔢 结果：**{result}**"
        except ZeroDivisionError:
            return "❌ 除数不能为 0"
        except Exception as e:
            return f"❌ 计算错误：{str(e)[:50]}"

    def _preprocess(self, expr: str) -> str:
        expr = expr.replace('^', '**').replace('×', '*').replace('÷', '/')
        expr = re.sub(r'(\d+)%', r'\1/100', expr)
        for const in self.CONSTANTS:
            expr = re.sub(r'(\d)({})'.format(const), r'\1*\2', expr)
        for func in self.MATH_FUNCTIONS:
            expr = re.sub(r'{}\('.format(func), lambda m, f=func: 'math.' + f + '(', expr)
        return expr

    def _extract_expression(self, text: str) -> Optional[str]:
        cleaned = text.strip()
        for prefix in ["计算", "等于多少", "求值", "帮我算", "请问"]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        cleaned = cleaned.rstrip('?？')
        match = re.search(r'([\d\s\+\-\*\/\(\)\^\.a-z]+)', cleaned, re.IGNORECASE)
        if match:
            expr = match.group(1).strip()
            if expr:
                return expr
        return None

    def _help(self) -> str:
        funcs = ", ".join(list(self.MATH_FUNCTIONS.keys())[:10])
        return f"""🔢 科学计算器

支持：+ - * / ^ ( ) % 
函数：{funcs}...
常量：pi, e

示例：sqrt(16) + 3^2, sin(pi/2), log(100), factorial(5)"""

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}


if __name__ == "__main__":
    agent = CalculatorAgentV4("test")
    print(agent.process("计算 sqrt(16) + 3^2")["response"])
