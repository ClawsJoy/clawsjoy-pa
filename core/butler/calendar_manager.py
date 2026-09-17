"""日历管理模块"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional


class CalendarManager:
    """日历管理器"""
    
    def __init__(self, user_id: str, memory):
        self.user_id = user_id
        self.memory = memory
    
    def add_event(self, title: str, start_time: str, end_time: str = None, 
                  date: str = None, location: str = "") -> bool:
        """添加日程事件"""
        events = self.memory.load_data('calendar_events') or []
        
        if end_time is None:
            end_time = (datetime.strptime(start_time, "%H:%M") + timedelta(hours=1)).strftime("%H:%M")
        
        events.append({
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "location": location,
            "created_at": datetime.now().isoformat()
        })
        self.memory.store_data('calendar_events', events)
        return True
    
    def get_today_events(self) -> List[Dict]:
        """获取今日日程"""
        today = datetime.now().strftime("%Y-%m-%d")
        events = self.memory.load_data('calendar_events') or []
        return [e for e in events if e.get('date') == today]
    
    def check_conflict(self, start_time: str, date: str = None) -> bool:
        """检查时间冲突"""
        date = date or datetime.now().strftime("%Y-%m-%d")
        events = self.memory.load_data('calendar_events') or []
        
        for e in events:
            if e.get('date') == date and e.get('start_time') == start_time:
                return True
        return False
    
    def get_weekly_schedule(self) -> Dict:
        """获取本周日程"""
        weekly = {}
        for i in range(7):
            day = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            events = [e for e in self.memory.load_data('calendar_events') or [] if e.get('date') == day]
            weekly[day] = events
        return weekly
