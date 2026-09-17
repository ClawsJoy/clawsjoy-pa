#!/usr/bin/env python3
"""数学大师智能体 - 高级数学计算"""

import math
import re
from typing import Dict, Optional

from core.agents.business.base_business_agent import BusinessAgent


class CalculatorAgent(BusinessAgent):
    """数学大师 - 高级数学计算"""

    name = "calculator_agent"
    description = "数学大师 - 高级数学计算"
    version = "2.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.history = []
        self.variables = {}
        print(f"🧮 数学大师 CalculatorAgent v2.0 已上线")

    def _execute_business(self, user_input: str, context: dict = None) -> dict:
        """业务逻辑实现 - BusinessAgent 要求"""
        return self.process(user_input, context)

    def _basic_calc(self, expr: str) -> Optional[Dict]:
        """基础四则运算"""
        match = re.search(r"(\d+(?:\.\d+)?)\s*([+\-*/])\s*(\d+(?:\.\d+)?)", expr)
        if match:
            a, op, b = float(match.group(1)), match.group(2), float(match.group(3))
            try:
                if op == "+":
                    result = a + b
                elif op == "-":
                    result = a - b
                elif op == "*":
                    result = a * b
                elif op == "/":
                    result = a / b if b != 0 else "除数不能为零"
                else:
                    return None

                self._save_history(f"{a}{op}{b}", result)
                return {
                    "success": True,
                    "response": f"{a}{op}{b} = {result}",
                    "agent": self.name,
                    "user_id": self.user_id,
                }
            except Exception:
                pass
        return None

    def _scientific_calc(self, expr: str) -> Optional[Dict]:
        """科学计算"""
        patterns = [
            (r"sin\((\d+(?:\.\d+)?)\)", lambda x: math.sin(math.radians(float(x)))),
            (r"cos\((\d+(?:\.\d+)?)\)", lambda x: math.cos(math.radians(float(x)))),
            (r"tan\((\d+(?:\.\d+)?)\)", lambda x: math.tan(math.radians(float(x)))),
            (r"sqrt\((\d+(?:\.\d+)?)\)", lambda x: math.sqrt(float(x))),
            (r"log\((\d+(?:\.\d+)?)\)", lambda x: math.log10(float(x))),
            (r"ln\((\d+(?:\.\d+)?)\)", lambda x: math.log(float(x))),
            (r"abs\((-?\d+(?:\.\d+)?)\)", lambda x: abs(float(x))),
            (
                r"pow\((\d+(?:\.\d+)?),(\d+(?:\.\d+)?)\)",
                lambda x, y: math.pow(float(x), float(y)),
            ),
        ]

        for pattern, func in patterns:
            match = re.search(pattern, expr, re.IGNORECASE)
            if match:
                args = [float(g) for g in match.groups()]
                result = func(*args)
                self._save_history(expr, result)
                return {
                    "success": True,
                    "response": f"{expr} = {result:.6f}",
                    "agent": self.name,
                    "user_id": self.user_id,
                }
        return None

    def _variable_calc(self, expr: str) -> Optional[Dict]:
        """变量赋值和使用"""
        # 赋值: a=5 或 设 a=5
        assign = re.search(r"(?:设\s*)?([a-zA-Z])\s*=\s*(\d+(?:\.\d+)?)", expr)
        if assign:
            var, val = assign.group(1), float(assign.group(2))
            self.variables[var] = val
            return {
                "success": True,
                "response": f"✅ 已设 {var} = {val}",
                "agent": self.name,
                "user_id": self.user_id,
            }

        # 使用变量: a+3
        for var, val in self.variables.items():
            if var in expr:
                new_expr = expr.replace(var, str(val))
                return self._basic_calc(new_expr) or self._scientific_calc(new_expr)
        return None

    def _unit_conversion(self, expr: str) -> Optional[Dict]:
        """单位转换"""
        units = {
            "cm": 0.01,
            "m": 1.0,
            "km": 1000.0,
            "mm": 0.001,
            "inch": 0.0254,
            "ft": 0.3048,
            "g": 0.001,
            "kg": 1.0,
            "lb": 0.4536,
        }

        match = re.search(r"(\d+(?:\.\d+)?)\s*([a-z]+)\s+to\s+([a-z]+)", expr, re.IGNORECASE)
        if match:
            val, from_unit, to_unit = (
                float(match.group(1)),
                match.group(2).lower(),
                match.group(3).lower(),
            )
            if from_unit in units and to_unit in units:
                result = val * units[from_unit] / units[to_unit]
                self._save_history(expr, result)
                return {
                    "success": True,
                    "response": f"{val}{from_unit} = {result:.4f}{to_unit}",
                    "agent": self.name,
                    "user_id": self.user_id,
                }
        return None

    def _complex_expr(self, expr: str) -> Optional[Dict]:
        """复杂表达式"""
        # 支持括号和优先级
        try:
            # 安全计算（只允许数字、运算符、括号）
            if re.match(r"^[\d\s\+\-\*/\(\)\.]+$", expr):
                result = eval(expr)
                self._save_history(expr, result)
                return {
                    "success": True,
                    "response": f"{expr} = {result}",
                    "agent": self.name,
                    "user_id": self.user_id,
                }
        except Exception:
            pass
        return None

    def _save_history(self, expr: str, result):
        """保存计算历史"""
        self.history.append(
            {
                "expr": expr,
                "result": str(result),
                "timestamp": __import__("time").time(),
            }
        )
        if len(self.history) > 20:
            self.history = self.history[-20:]
