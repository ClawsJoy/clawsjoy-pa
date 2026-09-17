#!/usr/bin/env python3
"""AST 静态分析器 - 替代纯 LLM 扫描"""

import ast
import sys
from typing import List, Dict, Any, Optional

sys.path.insert(0, '/home/flybo/clawsjoy_v5')


class ASTAnalyzer:
    """Python 代码 AST 静态分析器"""

    def __init__(self):
        self.issues: List[Dict] = []
        self.tree: Optional[ast.AST] = None
        self.code_lines: List[str] = []
        self.defined_names: set = set()
        self.used_names: set = set()

    def analyze(self, code: str, file_path: str = "") -> List[Dict]:
        """分析代码，返回问题列表"""
        self.issues = []
        self.code_lines = code.split('\n')
        self.defined_names = set()
        self.used_names = set()

        try:
            self.tree = ast.parse(code, filename=file_path)
        except SyntaxError as e:
            self.issues.append({
                'line': e.lineno,
                'type': 'syntax',
                'severity': 'high',
                'description': f'语法错误: {e.msg}',
                'suggestion': '修复语法错误'
            })
            return self.issues

        # 执行各种检查
        self._check_docstrings()
        self._check_unused_imports()
        self._check_exception_handling()
        self._check_function_length()
        self._check_too_many_arguments()
        self._check_global_variables()

        return self.issues

    def _check_docstrings(self):
        """检查函数/类是否缺少文档字符串"""
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    self.issues.append({
                        'line': node.lineno,
                        'type': 'documentation',
                        'severity': 'low',
                        'description': f'{node.name} 缺少文档字符串',
                        'suggestion': '添加 docstring 说明函数用途、参数和返回值'
                    })

    def _check_unused_imports(self):
        """检查未使用的导入"""
        imports = {}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports[alias.name] = node
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    imports[full_name] = node

        # 检查哪些导入被使用
        used_imports = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Name):
                if node.id in imports:
                    used_imports.add(node.id)

        for import_name, node in imports.items():
            if import_name not in used_imports:
                self.issues.append({
                    'line': node.lineno,
                    'type': 'style',
                    'severity': 'low',
                    'description': f'未使用的导入: {import_name}',
                    'suggestion': f'删除未使用的导入 {import_name}'
                })

    def _check_exception_handling(self):
        """检查异常处理"""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Try):
                # 检查是否有 except 子句
                if not node.handlers:
                    continue
                # 检查是否捕获了 Exception（过于宽泛）
                for handler in node.handlers:
                    if handler.type is None:
                        self.issues.append({
                            'line': handler.lineno,
                            'type': 'error_handling',
                            'severity': 'medium',
                            'description': '捕获了所有异常 (bare except)',
                            'suggestion': '指定具体的异常类型，如 except ValueError:'
                        })
                    elif isinstance(handler.type, ast.Name) and handler.type.id == 'Exception':
                        self.issues.append({
                            'line': handler.lineno,
                            'type': 'error_handling',
                            'severity': 'medium',
                            'description': '捕获了 Exception，过于宽泛',
                            'suggestion': '捕获更具体的异常类型'
                        })

    def _check_function_length(self):
        """检查函数长度"""
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = node.lineno
                end = node.end_lineno if hasattr(node, 'end_lineno') else start
                length = end - start
                if length > 50:
                    self.issues.append({
                        'line': start,
                        'type': 'complexity',
                        'severity': 'medium',
                        'description': f'函数 {node.name} 过长 ({length} 行)',
                        'suggestion': '将长函数拆分为多个小函数'
                    })

    def _check_too_many_arguments(self):
        """检查参数数量"""
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                arg_count = len(node.args.args)
                if arg_count > 5:
                    self.issues.append({
                        'line': node.lineno,
                        'type': 'complexity',
                        'severity': 'low',
                        'description': f'函数 {node.name} 有 {arg_count} 个参数',
                        'suggestion': '考虑使用 *args 或 **kwargs 减少参数数量'
                    })

    def _check_global_variables(self):
        """检查全局变量"""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Global):
                for name in node.names:
                    self.issues.append({
                        'line': node.lineno,
                        'type': 'style',
                        'severity': 'low',
                        'description': f'使用了 global 变量: {name}',
                        'suggestion': '避免使用全局变量，考虑封装到类中'
                    })


def analyze_code_ast(code: str, file_path: str = "") -> List[Dict]:
    """便捷函数：AST 分析代码"""
    analyzer = ASTAnalyzer()
    return analyzer.analyze(code, file_path)
