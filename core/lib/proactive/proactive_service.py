"""主动服务 - 基于情绪和习惯"""

import json
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict


class ProactiveService:
    """主动服务管理器"""
    
    def __init__(self):
        self._user_habits: Dict[str, Dict] = {}
        self._running = False
        self._load()
        print("💡 主动服务模块已启动")
    
    def _get_path(self) -> Path:
        return Path("data/proactive/habits.json")
    
    def _load(self):
        path = self._get_path()
        if path.exists():
            try:
                with open(path, 'r') as f:
                    self._user_habits = json.load(f)
            except:
                pass
    
    def _save(self):
        path = self._get_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self._user_habits, f, indent=2)
    
    def record_activity(self, user_id: str, activity: Dict):
        """记录用户活动"""
        if user_id not in self._user_habits:
            self._user_habits[user_id] = {
                "first_seen": datetime.now().isoformat(),
                "active_hours": [],
                "frequent_topics": defaultdict(int),
                "last_active": None,
                "total_interactions": 0
            }
        
        habit = self._user_habits[user_id]
        habit["total_interactions"] += 1
        habit["last_active"] = datetime.now().isoformat()
        
        # 记录活跃时间
        hour = datetime.now().hour
        habit["active_hours"].append(hour)
        habit["active_hours"] = habit["active_hours"][-50:]
        
        # 记录话题
        if "topic" in activity:
            habit["frequent_topics"][activity["topic"]] += 1
        
        self._save()
    
    def get_suggestion(self, user_id: str, emotion: str = None) -> Optional[str]:
        """获取主动建议"""
        if user_id not in self._user_habits:
            return None
        
        habit = self._user_habits[user_id]
        current_hour = datetime.now().hour
        
        # 基于时间建议
        if 6 <= current_hour < 9:
            return "☀️ 早上好！需要我帮您规划今天的工作吗？"
        if 11 <= current_hour < 14:
            return "🍜 午饭时间到了，需要帮您推荐餐厅吗？"
        if 21 <= current_hour < 23:
            return "🌙 晚安！需要设置明早的提醒吗？"
        
        # 基于情绪建议
        if emotion == "sad":
            return "🥺 看起来您心情不太好，需要聊聊天吗？"
        if emotion == "tired":
            return "😴 您看起来有点累，要不要休息一下？"
        
        # 基于活跃度
        if habit["total_interactions"] > 100:
            return "🏆 您是我们的活跃用户！有什么我可以帮您的吗？"
        
        return None
    
    def start(self):
        """启动后台服务"""
        if self._running:
            return
        self._running = True
        
        def _loop():
            while self._running:
                time.sleep(300)
        threading.Thread(target=_loop, daemon=True).start()


proactive_service = ProactiveService()
proactive_service.start()
