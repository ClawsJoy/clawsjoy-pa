"""安全计算器 - 替代 eval，防止代码注入"""

import ast
import operator
import math
from typing import Any, Union


class SafeCalculator:
    """安全数学计算器 - 不使用 eval"""
    
    # 支持的操作符
    _operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    
    @classmethod
    def calculate(cls, expression: str) -> Union[float, str]:
        """安全计算数学表达式"""
        try:
            # 只允许数字、运算符、括号和空格
            allowed_chars = set('0123456789+-*/().% ')
            if not all(c in allowed_chars for c in expression):
                raise ValueError("表达式包含非法字符")
            
            # 使用 ast 安全求值
            tree = ast.parse(expression, mode='eval')
            result = cls._eval_node(tree.body)
            return result
        except Exception as e:
            raise ValueError(f"计算错误: {e}")
    
    @classmethod
    def _eval_node(cls, node):
        """递归求值 AST 节点"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)
            op = cls._operators.get(type(node.op))
            if op:
                return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = cls._eval_node(node.operand)
            op = cls._operators.get(type(node.op))
            if op:
                return op(operand)
        elif isinstance(node, ast.Name):
            raise ValueError("变量名不允许")
        raise ValueError(f"不支持的表达式: {type(node)}")


safe_calculator = SafeCalculator()
