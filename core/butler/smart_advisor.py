"""智能建议模块 - 主动分析和建议"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional


class SmartAdvisor:
    """智能建议器"""
    
    def __init__(self, user_id: str, memory):
        self.user_id = user_id
        self.memory = memory
    
    def analyze_workload(self, todos: List[Dict]) -> Dict:
        """分析工作量"""
        pending = [t for t in todos if not t.get('completed', False)]
        completed = [t for t in todos if t.get('completed', False)]
        
        return {
            "total": len(todos),
            "pending": len(pending),
            "completed": len(completed),
            "completion_rate": len(completed) / max(len(todos), 1),
            "suggestion": self._get_workload_suggestion(len(pending))
        }
    
    def _get_workload_suggestion(self, pending_count: int) -> str:
        if pending_count > 10:
            return "您的待办较多，建议优先处理紧急事项"
        elif pending_count > 5:
            return "工作量适中，保持节奏即可"
        elif pending_count > 0:
            return "任务不多，可以轻松完成"
        else:
            return "暂无待办，可以休息一下"
    
    def suggest_priority(self, todos: List[Dict]) -> List[Dict]:
        """智能排序待办"""
        # 按创建时间排序，越早越优先
        sorted_todos = sorted(todos, key=lambda x: x.get('created_at', ''))
        return sorted_todos
    
    def get_daily_summary(self) -> str:
        """生成每日总结"""
        todos = self.memory.load_data('todos') or []
        completed = [t for t in todos if t.get('completed', False)]
        pending = [t for t in todos if not t.get('completed', False)]
        
        summary = f"📊 今日总结:\n"
        summary += f"   ✅ 完成: {len(completed)} 项\n"
        summary += f"   ⭕ 待办: {len(pending)} 项\n"
        
        if pending:
            summary += f"   📝 剩余任务:\n"
            for t in pending[:5]:
                summary += f"      • {t.get('task')}\n"
        
        return summary
