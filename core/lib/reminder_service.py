"""统一提醒服务 - 所有 Agent 共享"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional


@dataclass
class Reminder:
    id: str
    agent_name: str
    content: str
    remind_at: datetime
    repeat: str = None
    triggered: bool = False
    created_at: datetime = field(default_factory=datetime.now)


class ReminderService:
    """统一提醒服务 - 单例"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.reminders: List[Reminder] = []
        self._listeners: Dict[str, List[Callable]] = {}  # agent_name -> [callbacks]
        self._running = True
        self._start_checker()
        print("🔔 统一提醒服务已启动")

    def _start_checker(self):
        def check_loop():
            while self._running:
                try:
                    self._check_reminders()
                    time.sleep(10)
                except Exception as e:
                    print(f"提醒检查错误: {e}")

        thread = threading.Thread(target=check_loop, daemon=True)
        thread.start()

    def _check_reminders(self):
        now = datetime.now()
        for r in self.reminders:
            if not r.triggered and now >= r.remind_at:
                r.triggered = True
                self._notify_agent(r)

    def _notify_agent(self, reminder: Reminder):
        """通知对应 Agent"""
        if reminder.agent_name in self._listeners:
            for callback in self._listeners[reminder.agent_name]:
                try:
                    callback(reminder)
                except Exception as e:
                    print(f"通知失败: {e}")
        print(f"\n🔔 [{reminder.agent_name}] 提醒: {reminder.content}")

    def register_agent(self, agent_name: str, callback: Callable):
        """注册 Agent 的提醒回调"""
        if agent_name not in self._listeners:
            self._listeners[agent_name] = []
        self._listeners[agent_name].append(callback)

    def add_reminder(self, agent_name: str, content: str, remind_at: datetime) -> str:
        """添加提醒"""
        reminder_id = str(uuid.uuid4())[:8]
        reminder = Reminder(
            id=reminder_id, agent_name=agent_name, content=content, remind_at=remind_at
        )
        self.reminders.append(reminder)
        print(
            f"📅 [{agent_name}] 提醒已设置: {content} @ {remind_at.strftime('%H:%M')}"
        )
        return reminder_id

    def list_reminders(self, agent_name: str = None) -> List[Dict]:
        """列出提醒"""
        result = []
        for r in self.reminders:
            if agent_name is None or r.agent_name == agent_name:
                result.append(
                    {
                        "id": r.id,
                        "content": r.content,
                        "remind_at": r.remind_at.isoformat(),
                        "triggered": r.triggered,
                    }
                )
        return result


reminder_service = ReminderService()
