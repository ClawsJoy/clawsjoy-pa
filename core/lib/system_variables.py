"""系统变量管理 - 供话本使用"""

from datetime import datetime
from typing import Dict, Any


class SystemVariables:
    """系统变量提供者"""
    
    def __init__(self, agent):
        self.agent = agent
    
    def get_all(self, user_id: str) -> Dict[str, Any]:
        """获取所有系统变量"""
        return {
            # 用户变量
            "user_name": self.agent.recall_forever("user_name") if hasattr(self.agent, 'recall_forever') else None,
            "user_pref_color": self.agent.recall_forever("pref_color") if hasattr(self.agent, 'recall_forever') else None,
            "user_pref_food": self.agent.recall_forever("pref_food") if hasattr(self.agent, 'recall_forever') else None,
            
            # 时间变量
            "current_hour": datetime.now().hour,
            "current_time": datetime.now().strftime("%H:%M"),
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "is_morning": 6 <= datetime.now().hour < 12,
            "is_afternoon": 12 <= datetime.now().hour < 18,
            "is_evening": 18 <= datetime.now().hour < 22,
            "is_night": datetime.now().hour >= 22 or datetime.now().hour < 6,
            
            # Agent 变量
            "agent_name": getattr(self.agent, 'name', '小爪'),
            "agent_version": getattr(self.agent, 'version', '4.0.0'),
            
            # 会话变量
            "conversation_count": len(getattr(self.agent, '_conversation_history', [])),
        }


def get_system_variables(agent, user_id: str) -> Dict[str, Any]:
    """获取系统变量（供话本使用）"""
    return SystemVariables(agent).get_all(user_id)
