#!/usr/bin/env python3
"""Code Executor - Code Executor 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import re
import subprocess
import tempfile
from pathlib import Path


class CodeExecutor:
    """动态代码执行器"""

    name = "code_executor"

    def execute(self, goal: str, params: dict = None) -> dict:
        """动态生成并执行代码"""

        # 构建代码生成 prompt
        prompt = f"""根据用户需求生成 Python 代码来完成任务。

用户需求: {goal}

要求:
1. 只输出 Python 代码，不要解释
2. 代码必须能独立运行
3. 使用 print() 输出结果
4. 如果涉及外部依赖，使用 try/except 处理

代码:"""

        from core.lib.smart_adapter import smart_adapter

        code = smart_adapter.generate(prompt, auto_select=True)

        # 提取代码
        code = self._extract_code(code)
        if not code:
            return {"success": False, "error": "无法生成代码"}

        print(f"📝 生成代码: {code[:200]}...")

        # 执行代码
        try:
            result = self._run_code(code)
            return {
                "success": True,
                "result": result,
                "code_generated": True,
                "source": "code_executor",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_code(self, text: str) -> str:
        """提取代码块"""
        # 匹配 ```python ... ``` 或直接代码
        pattern = r"```(?:python)?\s*(.*?)```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 检查是否已经是代码
        if "def " in text or "import " in text or "print(" in text:
            return text.strip()

        return None

    def _run_code(self, code: str) -> str:
        """在沙箱中执行代码"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            result = subprocess.run(
                ["python3", temp_file], capture_output=True, text=True, timeout=30
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]: {result.stderr}"
            return output.strip() or "执行完成（无输出）"
        finally:
            Path(temp_file).unlink(missing_ok=True)


code_executor = CodeExecutor()
