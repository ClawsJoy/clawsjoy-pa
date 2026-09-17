#!/usr/bin/env python3
"""Priority Adjuster V1 0 00 20260517 - Priority Adjuster V1 0 00 20260517 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""优先级动态调整器 v1.0.00"""

from datetime import datetime
from typing import Dict, List


class PriorityAdjuster:
    """根据任务历史动态调整优先级"""

    VERSION = "1.0.00"

    def __init__(self):
        self.history = {}

    def adjust_priority(
        self, task_name: str, current_priority: int, success_rate: float = None
    ) -> int:
        """动态调整优先级"""

        # 高成功率任务降低优先级（让新任务有机会）
        if success_rate and success_rate > 0.9:
            return max(0, current_priority - 1)

        # 新任务（无历史）提升优先级
        if task_name not in self.history:
            return min(3, current_priority + 1)

        # 历史失败多的任务降低优先级
        fail_count = self.history.get(task_name, {}).get("fail_count", 0)
        if fail_count > 3:
            return max(0, current_priority - 2)

        return current_priority

    def record_outcome(self, task_name: str, success: bool):
        """记录任务结果"""
        if task_name not in self.history:
            self.history[task_name] = {"success": 0, "fail": 0, "last_seen": None}

        if success:
            self.history[task_name]["success"] += 1
        else:
            self.history[task_name]["fail"] += 1

        self.history[task_name]["last_seen"] = datetime.now().isoformat()

    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "total_tasks": len(self.history),
            "high_success_tasks": sum(
                1
                for h in self.history.values()
                if h.get("success", 0) > h.get("fail", 0)
            ),
            "high_fail_tasks": sum(
                1
                for h in self.history.values()
                if h.get("fail", 0) > h.get("success", 0)
            ),
        }


priority_adjuster = PriorityAdjuster()
