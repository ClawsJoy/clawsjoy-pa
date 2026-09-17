#!/usr/bin/env python3
"""Skill Validator - Skill Validator 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import ast
import re

from core.lib.unified_config import unified_config


class SkillValidator:
    DANGEROUS_PATTERNS = [
        (r"os\.system", "执行系统命令"),
        (r"os\.popen", "执行系统命令"),
        (r"subprocess\.", "子进程调用"),
        (r"eval\s*\(", "eval 执行"),
        (r"exec\s*\(", "exec 执行"),
        (r"__import__", "动态导入"),
        (r'open\s*\([^)]*[\'"][rw]', "文件写入"),
        (r"requests\.(get|post|put|delete)", "网络请求"),
        (r"pickle\.load", "反序列化"),
    ]

    # 允许的导入
    ALLOWED_IMPORTS = [
        "json",
        "time",
        "datetime",
        "pathlib",
        "sys",
        "hashlib",
        "base64",
        "PIL",
        "collections",
        "itertools",
        "math",
        "random",
    ]

    # 允许的 os 操作
    ALLOWED_OS = [
        "path",
        "makedirs",
        "exists",
        "dirname",
        "basename",
        "join",
        "splitext",
    ]

    @classmethod
    def validate(cls, code):
        issues = []

        # 危险模式检查
        for pattern, desc in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                issues.append(f"危险模式: {desc}")

        # AST 检查
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.name
                        if name == "os":
                            continue  # 允许 import os
                        elif name not in cls.ALLOWED_IMPORTS:
                            issues.append(f"不允许的导入: {name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module
                    if module == "os":
                        continue  # 允许 from os import xxx
                    elif module not in cls.ALLOWED_IMPORTS:
                        issues.append(f"不允许的导入: {module}")
                elif isinstance(node, ast.Attribute):
                    # 检查 os.xxx
                    if isinstance(node.value, ast.Name) and node.value.id == "os":
                        if node.attr not in cls.ALLOWED_OS:
                            issues.append(f"不安全的 os 操作: os.{node.attr}")
        except SyntaxError as e:
            issues.append(f"语法错误: {e}")

        return {
            "safe": len(issues) == 0,
            "issues": issues,
            "risk_level": "low" if len(issues) == 0 else "medium",
        }
