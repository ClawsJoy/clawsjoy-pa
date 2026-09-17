"""Watchdog 核心 - OpenClaw 风格"""

import threading
import time
from datetime import datetime, timedelta
from typing import List, Callable, Optional, Dict, Any

from .state import WatchdogState, HealthStatus
from .checker import Checker, FileMtimeChecker


class Watchdog:
    """OpenClaw 风格 Watchdog - 分层决策、静默运行"""

    def __init__(self, name: str = "watchdog"):
        self.name = name
        self.state = WatchdogState()
        self._checkers: List[Checker] = []
        self._handlers: List[Callable] = []
        self._running = False
        self._thread = None
        self._suppress_until = None
        self._last_log = 0

    def add_checker(self, checker: Checker):
        """添加检测器"""
        self._checkers.append(checker)

    def on_alert(self, handler: Callable):
        """注册告警处理器"""
        self._handlers.append(handler)

    def _should_log(self, interval: int = 60) -> bool:
        """每分钟最多打印一次"""
        now = time.time()
        if now - self._last_log >= interval:
            self._last_log = now
            return True
        return False

    def _should_run(self) -> bool:
        if self._suppress_until and datetime.now() < self._suppress_until:
            return False
        return True

    def _run_checkers(self) -> HealthStatus:
        """分层决策运行检测器"""
        for c in self._checkers:
            if c.cost == "low":
                result = c.check()
                if result.get("exists") is False:
                    if self._should_log():
                        print(f"⚠️ [{self.name}] file not found")
                    return HealthStatus.DEGRADED
                if result.get("changed"):
                    if self._should_log():
                        print(f"🔄 [{self.name}] config changed")
                    return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def _alert(self, status: HealthStatus, message: str):
        """触发告警"""
        now = datetime.now()
        self.state.last_alert = now
        self._suppress_until = now + timedelta(minutes=10)

        for handler in self._handlers:
            try:
                handler(status, message)
            except Exception:
                pass

    def _loop(self):
        """主循环"""
        while self._running:
            try:
                if not self._should_run():
                    time.sleep(30)
                    continue

                new_status = self._run_checkers()
                self.state.total_checks += 1

                if new_status != self.state.status:
                    self.state.status = new_status
                    if new_status != HealthStatus.HEALTHY:
                        self._alert(new_status, f"{self.name} status changed")

                if self.state.status == HealthStatus.HEALTHY:
                    time.sleep(60)
                else:
                    time.sleep(30)

            except Exception as e:
                if self._should_log(10):
                    print(f"⚠️ [{self.name}] error: {e}")
                time.sleep(30)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
