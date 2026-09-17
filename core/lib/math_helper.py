#!/usr/bin/env python3
"""数学问题辅助函数"""

import re
from typing import Optional, Tuple

class MathHelper:
    """数学问题识别和修复"""
    
    @staticmethod
    def is_water_tank_problem(question: str) -> bool:
        """识别水池问题"""
        keywords = ['进水', '出水', '水池', '注满', '排空', '小时']
        return sum(1 for kw in keywords if kw in question) >= 2
    
    @staticmethod
    def extract_numbers_from_question(question: str) -> list:
        """从问题中提取数字，排除明显不是参数的数字"""
        # 提取所有数字
        all_numbers = re.findall(r'(\d+(?:\.\d+)?)', question)
        
        # 如果是水池问题，尝试找出合理的进水/出水时间（通常是小数字）
        if MathHelper.is_water_tank_problem(question):
            # 过滤掉太大的数字（比如之前计算的结果）
            reasonable = [n for n in all_numbers if float(n) <= 24]
            if len(reasonable) >= 2:
                return reasonable[:2]
            return all_numbers[:2]
        
        return all_numbers
    
    @staticmethod
    def solve_water_tank(inflow: float, outflow: float) -> Optional[str]:
        """解决水池问题"""
        if inflow <= 0 or outflow <= 0:
            return None
        
        inflow_rate = 1 / inflow
        outflow_rate = 1 / outflow
        
        if inflow_rate <= outflow_rate:
            return "进水速度小于或等于出水速度，水池永远无法注满。"
        
        net_rate = inflow_rate - outflow_rate
        time_needed = 1 / net_rate
        
        return f"""需要 {time_needed:.1f} 小时才能注满水池。

解题步骤：
• 进水管每小时注水：1/{inflow:.0f} = {inflow_rate:.3f}
• 出水管每小时排水：1/{outflow:.0f} = {outflow_rate:.3f}
• 净注水速率：{inflow_rate:.3f} - {outflow_rate:.3f} = {net_rate:.3f}
• 所需时间：1 ÷ {net_rate:.3f} = {time_needed:.1f} 小时

答案：{time_needed:.1f} 小时"""

math_helper = MathHelper()
