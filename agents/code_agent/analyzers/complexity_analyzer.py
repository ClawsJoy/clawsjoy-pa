#!/usr/bin/env python3
"""圈复杂度检测器"""

import ast
import sys
from typing import List, Dict, Optional

sys.path.insert(0, '/home/flybo/clawsjoy_v5')


class ComplexityAnalyzer:
    """圈复杂度分析器"""

    def __init__(self):
        self.complexity = 0

    def calculate(self, code: str) -> List[Dict]:
        """计算代码中每个函数的圈复杂度"""
        results = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return [{'error': '语法错误，无法解析代码'}]

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = self._calculate_function_complexity(node)
                if complexity > 10:
                    results.append({
                        'line': node.lineno,
                        'name': node.name,
                        'complexity': complexity,
                        'severity': 'high' if complexity > 20 else 'medium',
                        'description': f'函数 {node.name} 圈复杂度为 {complexity}',
                        'suggestion': f'建议拆分函数，将复杂度降低到 10 以下'
                    })

        return results

    def _calculate_function_complexity(self, node: ast.FunctionDef) -> int:
        """计算单个函数的圈复杂度"""
        complexity = 1  # 基础复杂度

        for child in ast.walk(node):
            # 分支语句
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            # 短路逻辑运算符
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            # 异常处理
            elif isinstance(child, ast.Try):
                complexity += len(child.handlers) + (1 if child.finalbody else 0)
            # 条件表达式
            elif isinstance(child, ast.IfExp):
                complexity += 1
            # 列表推导/生成器表达式中的 if
            elif isinstance(child, ast.comprehension):
                if child.ifs:
                    complexity += len(child.ifs)

        return complexity


def calculate_complexity(code: str) -> List[Dict]:
    """便捷函数：计算圈复杂度"""
    analyzer = ComplexityAnalyzer()
    return analyzer.calculate(code)
