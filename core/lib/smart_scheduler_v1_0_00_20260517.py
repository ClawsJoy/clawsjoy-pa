#!/usr/bin/env python3
"""Smart Scheduler V1 0 00 20260517 - Smart Scheduler V1 0 00 20260517 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""智能调度器 v1.0.00 - 基于预测的智能任务调度"""

import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from core.lib.config_driver import config_driver
from core.lib.success_predictor import success_predictor
from core.lib.task_queue import Priority, task_queue


class SmartScheduler:
    """智能调度器 - 动态调整任务优先级和调度策略"""

    VERSION = "1.0.00"

    def __init__(self):
        self.enabled = config_driver.get("optimization.enable_smart_scheduling", True)
        self.high_priority_threshold = config_driver.get(
            "thresholds.high_priority_rate", 0.8
        )
        self.low_priority_threshold = config_driver.get(
            "thresholds.low_priority_rate", 0.3
        )
        self.schedule_cache = {}

    def get_optimal_priority(self, task_name: str, current_priority: int) -> int:
        """获取最优优先级"""
        if not self.enabled:
            return current_priority

        # 获取预测
        prediction = success_predictor.predict_task_success_rate(task_name)
        predicted_rate = prediction["predicted_rate"]

        # 基于预测率调整优先级
        if predicted_rate >= self.high_priority_threshold:
            # 高成功率任务提升优先级
            return min(Priority.CRITICAL.value, current_priority + 1)
        elif predicted_rate <= self.low_priority_threshold:
            # 低成功率任务降低优先级
            return max(Priority.LOW.value, current_priority - 1)

        return current_priority

    def should_execute_now(self, task_name: str) -> Tuple[bool, str]:
        """判断是否应该立即执行"""
        if not self.enabled:
            return True, "调度器已禁用"

        prediction = success_predictor.predict_task_success_rate(task_name)

        # 如果预测率太低且置信度高，建议延迟执行
        if prediction["predicted_rate"] < 0.3 and prediction["confidence"] > 0.7:
            return (
                False,
                f"预测成功率低 ({prediction['predicted_rate']*100:.0f}%)，建议优化后再执行",
            )

        # 如果趋势下降，建议谨慎
        if prediction["trend"] == "declining" and prediction["total_samples"] > 5:
            return False, f"任务成功率呈下降趋势"

        return True, "可以执行"

    def get_execution_order(self, tasks: List) -> List:
        """获取优化后的执行顺序"""
        if not self.enabled:
            return tasks

        # 按预测成功率排序
        scored_tasks = []
        for task in tasks:
            prediction = success_predictor.predict_task_success_rate(task.name)
            scored_tasks.append(
                (prediction["predicted_rate"], prediction["confidence"], task)
            )

        # 高成功率、高置信度的任务优先
        scored_tasks.sort(key=lambda x: (x[0], x[1]), reverse=True)

        return [task for _, _, task in scored_tasks]

    def get_schedule_stats(self) -> Dict:
        """获取调度统计"""
        return {
            "version": self.VERSION,
            "enabled": self.enabled,
            "high_threshold": self.high_priority_threshold,
            "low_threshold": self.low_priority_threshold,
            "cache_size": len(self.schedule_cache),
        }


smart_scheduler = SmartScheduler()


if __name__ == "__main__":
    print(f"智能调度器 v{smart_scheduler.VERSION}")
    print(f"统计: {smart_scheduler.get_schedule_stats()}")

    # 测试
    test_tasks = ["[热度100] 制作视频: 香港高才通", "[TEST] 测试任务"]
    for task in test_tasks:
        should, reason = smart_scheduler.should_execute_now(task)
        print(f"\n任务: {task}")
        print(f"  立即执行: {should}")
        print(f"  原因: {reason}")
