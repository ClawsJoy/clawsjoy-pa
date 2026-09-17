#!/usr/bin/env python3
"""Dependency Checker - Dependency Checker 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""依赖检查器 - 检查代码依赖"""
import re
import subprocess
import sys


class DependencyChecker:
    @staticmethod
    def extract_imports(code):
        """提取代码中的导入"""
        imports = []
        patterns = [
            r"^import (\w+)",
            r"^from (\w+) import",
            r"^from (\w+)\.",
        ]
        for line in code.split("\n"):
            for pattern in patterns:
                match = re.match(pattern, line.strip())
                if match:
                    imports.append(match.group(1))
        return list(set(imports))

    @staticmethod
    def check_installed(package):
        """检查包是否已安装"""
        result = subprocess.run(
            [sys.executable, "-c", f"import {package.split('.')[0]}"],
            capture_output=True,
        )
        return result.returncode == 0

    @staticmethod
    def check_all(code):
        """检查所有依赖"""
        imports = DependencyChecker.extract_imports(code)
        missing = []
        stdlib = [
            "os",
            "sys",
            "json",
            "time",
            "datetime",
            "pathlib",
            "re",
            "math",
            "random",
            "collections",
            "itertools",
        ]
        for imp in imports:
            if imp not in stdlib:
                if not DependencyChecker.check_installed(imp):
                    missing.append(imp)
        return missing
