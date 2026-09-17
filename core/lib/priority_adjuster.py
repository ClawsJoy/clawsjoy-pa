#!/usr/bin/env python3
"""Priority Adjuster - Priority Adjuster 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""优先级调整器 v1.0.01 - 配置驱动版"""

from datetime import datetime
from typing import Dict

from core.lib.config_loader import config


class PriorityAdjuster:
    VERSION = "1.0.01"

    def __init__(self):
        self.enabled = config.get("optimization.enable_priority_adjust", True)
        self.history = {}
        self.history_window = config.get("optimization.history_window_size", 100)

    def adjust_priority(
        self, task_name: str, current_priority: int, success_rate: float = None
    ) -> int:
        if not self.enabled:
            return current_priority

        history = self.history.get(task_name, {"success": 0, "fail": 0})
        total = history["success"] + history["fail"]

        if total > 0:
            actual_rate = history["success"] / total
            if actual_rate > 0.8:
                return min(3, current_priority + 1)
            elif actual_rate < 0.3:
                return max(0, current_priority - 1)

        return current_priority

    def record_outcome(self, task_name: str, success: bool):
        if task_name not in self.history:
            self.history[task_name] = {"success": 0, "fail": 0, "last_seen": None}

        if success:
            self.history[task_name]["success"] += 1
        else:
            self.history[task_name]["fail"] += 1

        self.history[task_name]["last_seen"] = datetime.now().isoformat()

        if len(self.history) > self.history_window:
            oldest = min(
                self.history.keys(),
                key=lambda k: self.history[k].get("last_seen", "2000-01-01"),
            )
            del self.history[oldest]

    def get_stats(self) -> Dict:
        total = len(self.history)
        high_success = sum(
            1 for h in self.history.values() if h.get("success", 0) > h.get("fail", 0)
        )
        high_fail = sum(
            1 for h in self.history.values() if h.get("fail", 0) > h.get("success", 0)
        )

        return {
            "total_tasks": total,
            "high_success_tasks": high_success,
            "high_fail_tasks": high_fail,
            "enabled": self.enabled,
            "version": self.VERSION,
        }

    def get_status(self) -> Dict:
        return {
            "version": self.VERSION,
            "enabled": self.enabled,
            "tracked_tasks": len(self.history),
        }


priority_adjuster = PriorityAdjuster()
