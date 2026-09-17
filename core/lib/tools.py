"""工具集成模块 - 扩展系统能力"""

import subprocess
import json
from core.lib.safe_calculator import safe_calculator
import re
from datetime import datetime
from typing import Optional, Dict, Any

class ToolManager:
    """工具管理器"""
    
    @staticmethod
    def get_current_time() -> str:
        """获取当前时间"""
        now = datetime.now()
        return f"当前时间：{now.strftime('%Y年%m月%d日 %H:%M:%S')}（星期{now.strftime('%w')}）"
    
    @staticmethod
    def calculate(expression: str) -> Optional[str]:
        """安全计算表达式"""
        # 只允许数字和基本运算符
        if not re.match(r'^[\d\s\+\-\*\/\(\)\.]+$', expression):
            return None
        
        try:
            # 使用 eval 但限制在安全范围内
            result = safe_calculator.calculate(expression)
            return f"{expression} = {result}"
        except Exception:
            return None
    
    @staticmethod
    def extract_json(text: str) -> Optional[Dict]:
        """从文本中提取 JSON"""
        try:
            # 查找 JSON 块
            match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            
            # 查找直接 JSON
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception:
            pass
        return None
    
    @staticmethod
    def format_table(data: list, headers: list) -> str:
        """格式化表格"""
        if not data:
            return "无数据"
        
        # 计算列宽
        col_widths = [len(h) for h in headers]
        for row in data:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # 构建表格
        lines = []
        # 表头
        header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
        lines.append(header_line)
        lines.append("|" + "|".join("-" * (w + 2) for w in col_widths) + "|")
        
        # 数据行
        for row in data:
            line = "| " + " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)) + " |"
            lines.append(line)
        
        return "\n".join(lines)

tool_manager = ToolManager()
