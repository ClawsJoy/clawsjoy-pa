"""智能提醒模块"""

import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Callable


class SmartReminder:
    """智能提醒器"""
    
    def __init__(self, user_id: str, memory, callback=None):
        self.user_id = user_id
        self.memory = memory
        self.callback = callback
        self.running = False
        self._start_monitor()
    
    def _start_monitor(self):
        """启动提醒监控"""
        self.running = True
        thread = threading.Thread(target=self._monitor_loop, daemon=True)
        thread.start()
    
    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                self._check_reminders()
                self._check_conditions()
            except:
                pass
            time.sleep(60)  # 每分钟检查一次
    
    def _check_reminders(self):
        """检查提醒"""
        reminders = self.memory.load_data('reminders') or []
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.strftime("%Y-%m-%d")
        
        for r in reminders:
            if r.get('completed'):
                continue
            
            if r.get('time') == current_time and r.get('date') == current_date:
                self._trigger_reminder(r)
                r['completed'] = True
                self.memory.store_data('reminders', reminders)
    
    def _check_conditions(self):
        """检查条件触发提醒"""
        # 位置提醒（需要位置服务）
        # 天气提醒（需要天气API）
        pass
    
    def _trigger_reminder(self, reminder: Dict):
        """触发提醒"""
        message = f"🔔 提醒：{reminder.get('title')} 时间到了！"
        if self.callback:
            self.callback(self.user_id, message)
        print(f"[提醒] {self.user_id}: {message}")
    
    def add_condition_reminder(self, title: str, condition: str, target: str):
        """添加条件触发提醒"""
        conditions = self.memory.load_data('condition_reminders') or []
        conditions.append({
            "title": title,
            "condition": condition,
            "target": target,
            "completed": False
        })
        self.memory.store_data('condition_reminders', conditions)
