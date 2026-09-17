#!/usr/bin/env python3
"""Smart Active Loop - Smart Active Loop 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import threading
import time
from datetime import datetime

from core.lib.proactive_service import ProactiveService
from core.lib.smart_active_service import SmartActiveService


class SmartActiveLoop:
    """智能主动服务循环"""

    def __init__(self):
        self._running = False
        self._smart_service = SmartActiveService()
        self._proactive_service = ProactiveService()
        self._last_greeting_date = None

    def start(self):
        """启动主动服务循环"""
        if self._running:
            return
        self._running = True
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()
        print("✅ 智能主动服务循环已启动")

    def stop(self):
        self._running = False

    def _run(self):
        while self._running:
            try:
                # 1. 每小时执行一次维护任务
                self._proactive_service.clear_cache()

                # 2. 检查是否需要主动服务
                context = {
                    "first_interaction": self._is_first_interaction_today(),
                    "task_completed": False,  # 可以从事件总线获取
                    "error_detected": False,  # 可以从日志获取
                }

                result = self._smart_service.should_serve("personal_butler", context)
                if result.get("should"):
                    self._execute_action(result)

                time.sleep(3600)  # 每小时检查一次
            except Exception as e:
                print(f"主动服务循环错误: {e}")
                time.sleep(60)

    def _is_first_interaction_today(self):
        """检查是否是今天的第一次交互"""
        today = datetime.now().date()
        if self._last_greeting_date != today:
            self._last_greeting_date = today
            return True
        return False

    def _execute_action(self, result):
        """执行主动服务动作"""
        reason = result.get("reason")
        if reason == "morning_greeting":
            print("🌅 发送早安问候")
            # 可以调用 webhook 或发送通知
        elif reason == "task_completed":
            print("✅ 任务完成，询问是否需要帮助")
        elif reason == "help_needed":
            print("🆘 检测到问题，主动提供帮助")
        elif reason == "todo_reminder":
            print("📋 检查待办事项提醒")


smart_loop = SmartActiveLoop()
