"""数学计算执行器"""

import re


class MathExecutor:
    """数学计算执行器"""

    name = "math_executor"

    def execute(self, goal: str, params: dict = None) -> dict:
        """执行数学计算"""
        # 提取数学表达式
        expr = re.sub(r"[^0-9+\-*/().]", "", goal)
        if expr:
            try:
                # 安全检查
                if any(op in expr for op in ["__", "import", "eval", "exec"]):
                    return {"result": "不支持的计算", "success": False}
                result = eval(expr)
                return {
                    "result": f"计算结果: {result}",
                    "response": f"计算结果: {result}",
                    "success": True,
                }
            except Exception as e:
                pass
        return {
            "result": "无法计算",
            "success": False,
            "response": "无法计算，请提供正确的算式",
        }


math_executor = MathExecutor()
