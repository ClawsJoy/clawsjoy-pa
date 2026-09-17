"""生命周期 Mixin - 唤醒、沉睡、梦境"""

import threading
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional


class LifecycleMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lifecycle_state = "sleeping"
        self._state = {}  # 业务状态字典
    """生命周期混入类 - 让 Agent 拥有完整的生命周期"""

    def _init_lifecycle(self):
        """初始化生命周期（在 Agent __init__ 中调用）"""
        self._lifecycle_state = "sleeping"  # sleeping, waking, active, dreaming
        self._last_wake = None
        self._last_dream = None
        self._wake_count = 0
        self._dream_count = 0
        self._lifecycle_running = True
        self._start_lifecycle_loop()
        self._init_task_queue()
        self._init_reminder()
        self.log(f"生命周期已启动，初始状态: sleeping")

    def _start_lifecycle_loop(self):
        """启动生命周期循环（独立线程）"""

        def loop():
            while self._lifecycle_running:
                try:
                    if self._lifecycle_state == "sleeping":
                        if self._should_wake():
                            self._wake_up()

                    elif self._lifecycle_state == "active":
                        self._do_routine()
                        self._go_to_dream()

                    elif self._lifecycle_state == "dreaming":
                        self._do_dream()
                        self._lifecycle_state = "sleeping"

                    time.sleep(60)
                    # 🔧 确保 _state 是字典（防御性编程）
                    if hasattr(self, "_state") and not isinstance(self._state, dict):
                        self._state = {}
                    if hasattr(self, "_state") and "total_interactions" not in self._state:
                        self._state["total_interactions"] = 0
                    if hasattr(self, "_stats") and not isinstance(self._stats, dict):
                        self._stats = {}
                    if hasattr(self, "_stats") and "total_interactions" not in self._stats:
                        self._stats["total_interactions"] = 0


                except Exception as e:
                    print(f"[{self.name}] 生命周期错误: {e}")
                    self._lifecycle_state = "sleeping"

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()

    def _should_wake(self) -> bool:
        """判断是否需要唤醒（默认每60秒）"""
        if self._last_wake is None:
            return True
        elapsed = (datetime.now() - self._last_wake).total_seconds()
        return elapsed >= 300

    def _wake_up(self):
        """唤醒"""
        self._lifecycle_state = "waking"
        self._last_wake = datetime.now()
        self._wake_count += 1
        self.log(f"🌞 唤醒 (第{self._wake_count}次)")

        if hasattr(self, "health_check"):
            health = self.health_check()
            self.log(f"🏥 健康检查: {health.get('status', 'ok')}")

        self._lifecycle_state = "active"

    def _do_routine(self):
        """执行例行任务（子类可覆盖）"""
        # 🔧 确保状态是字典
        if not hasattr(self, "_state") or not isinstance(self._state, dict):
            self._state = {}
        if "total_interactions" not in self._state:
            self._state["total_interactions"] = 0

        self.log(f"⚙️ 执行例行任务...")

    def _go_to_dream(self):
        """进入梦境"""
        # 🔧 确保状态是字典
        if not hasattr(self, "_state") or not isinstance(self._state, dict):
            self._state = {}
        if "total_interactions" not in self._state:
            self._state["total_interactions"] = 0

        self._lifecycle_state = "dreaming"
        self._last_dream = datetime.now()
        self._dream_count += 1
        self.log(f"💭 进入梦境 (第{self._dream_count}次)")

    def _do_dream(self):
        """梦境中：整理记忆、学习（子类可覆盖）"""
        if hasattr(self, "_permanent_memory"):
            self.log(f"📚 整理记忆...")
        time.sleep(1)

    def get_lifecycle_status(self) -> Dict:
        """获取生命周期状态"""
        return {
            "state": self._lifecycle_state,
            "last_wake": self._last_wake.isoformat() if self._last_wake else None,
            "last_dream": self._last_dream.isoformat() if self._last_dream else None,
            "wake_count": self._wake_count,
            "dream_count": self._dream_count,
        }

    def wake_now(self):
        """立即唤醒"""
        self._wake_up()

    def _init_task_queue(self):
        """初始化任务队列"""
        try:
            from core.lib.task_queue import task_queue

            self._task_queue = task_queue
        except Exception as e:
            pass

    def submit_task(self, func: Callable, *args, callback: Callable = None, **kwargs):
        """提交异步任务"""
        if hasattr(self, "_task_queue"):
            self._task_queue.submit(func, *args, callback=callback, **kwargs)
            self.log(f"📋 任务已提交: {func.__name__}")

    def _init_reminder(self):
        """初始化提醒服务"""
        try:
            from core.lib.reminder_service import reminder_service

            reminder_service.register_agent(self.name, self._on_reminder)
            self._reminder_service = reminder_service
        except Exception as e:
            pass

    def _on_reminder(self, reminder):
        """收到提醒时的回调"""
        self.log(f"🔔 收到提醒: {reminder.content}")

    def set_reminder(self, content: str, remind_at: datetime) -> str:
        """设置提醒"""
        if hasattr(self, "_reminder_service"):
            return self._reminder_service.add_reminder(self.name, content, remind_at)
        return None

    # ========== 钩子函数 ==========
    def on_init(self):
        pass

    def on_start(self):
        pass

    def on_stop(self):
        pass

    def on_error(self, error: Exception):
        self.log(f"错误: {error}", "ERROR")

    def on_success(self, result: Dict):
        pass

    def _update_stats(self):
        self._stats = {
            "processed": 0,
            "success": 0,
            "errors": 0,
            "started_at": None,
            "last_active": datetime.now().isoformat(),
        }

    def _increment_stats(self, key: str):
        if hasattr(self, "_stats") and key in self._stats:
            self._stats[key] += 1

    def get_stats(self) -> Dict:
        if hasattr(self, "_stats"):
            self._stats["last_active"] = datetime.now().isoformat()
            return self._stats
        return {}

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        agent_name = getattr(self, "name", "unknown")
        print(f"[{timestamp}] [{agent_name}] [{level}] {message}")
