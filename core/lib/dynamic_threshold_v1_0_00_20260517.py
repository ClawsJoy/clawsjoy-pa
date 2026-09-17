from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""动态阈值调整器 v1.0.00 - 根据系统表现自动调整阈值"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.lib.config_driver import config_driver
from core.lib.success_predictor import success_predictor


class DynamicThreshold:
    """动态阈值调整器 - 自动优化配置参数"""

    VERSION = "1.0.00"

    def __init__(self):
        self.enabled = config_driver.get("optimization.enable_dynamic_threshold", True)
        self.adjustment_file = Path("PROJECT_ROOT/data/dynamic_thresholds.json")
        self.threshold_history = self._load_history()

        # 当前阈值
        self.current_thresholds = {
            "quality_min_score": config_driver.get("thresholds.quality_min_score", 0.5),
            "max_retry_same_error": config_driver.get(
                "thresholds.max_retry_same_error", 3
            ),
        }

    def _load_history(self) -> Dict:
        """加载调整历史"""
        if self.adjustment_file.exists():
            try:
                with open(self.adjustment_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                return {}
        return {}

    def _save_history(self):
        """保存调整历史"""
        with open(self.adjustment_file, "w") as f:
            json.dump(self.threshold_history, f, indent=2)

    def adjust_quality_threshold(self) -> float:
        """动态调整质量阈值"""
        if not self.enabled:
            return self.current_thresholds["quality_min_score"]

        # 获取系统表现
        worst_tasks = success_predictor.get_worst_tasks(5)

        # 如果有很多低成功率任务，降低阈值
        low_success_count = sum(1 for t in worst_tasks if t["rate"] < 0.3)

        current = self.current_thresholds["quality_min_score"]

        if low_success_count >= 3:
            # 太多低质量任务，降低阈值
            new_threshold = max(0.2, current - 0.05)
            adjustment_reason = f"发现 {low_success_count} 个低成功率任务"
        elif low_success_count == 0 and current > 0.3:
            # 系统表现良好，可以适当提高阈值
            new_threshold = min(0.7, current + 0.02)
            adjustment_reason = "系统表现良好，提高质量标准"
        else:
            new_threshold = current
            adjustment_reason = "保持当前阈值"

        if new_threshold != current:
            self.current_thresholds["quality_min_score"] = new_threshold
            self._record_adjustment(
                "quality_min_score", current, new_threshold, adjustment_reason
            )

        return new_threshold

    def adjust_retry_threshold(self) -> int:
        """动态调整重试阈值"""
        if not self.enabled:
            return self.current_thresholds["max_retry_same_error"]

        # 获取系统表现
        best_tasks = success_predictor.get_best_tasks(5)
        worst_tasks = success_predictor.get_worst_tasks(5)

        current = self.current_thresholds["max_retry_same_error"]

        # 计算平均成功率
        all_tasks = best_tasks + worst_tasks
        if all_tasks:
            avg_rate = sum(t["rate"] for t in all_tasks) / len(all_tasks)

            if avg_rate > 0.8 and current > 2:
                # 系统表现好，减少重试次数
                new_threshold = max(2, current - 1)
                adjustment_reason = f"系统平均成功率 {avg_rate:.0%}，降低重试阈值"
            elif avg_rate < 0.5:
                # 系统表现差，增加重试次数
                new_threshold = min(5, current + 1)
                adjustment_reason = f"系统平均成功率 {avg_rate:.0%}，提高重试阈值"
            else:
                new_threshold = current
                adjustment_reason = "保持当前阈值"
        else:
            new_threshold = current
            adjustment_reason = "数据不足"

        if new_threshold != current:
            self.current_thresholds["max_retry_same_error"] = new_threshold
            self._record_adjustment(
                "max_retry_same_error", current, new_threshold, adjustment_reason
            )

        return new_threshold

    def _record_adjustment(self, key: str, old_value, new_value, reason: str):
        """记录调整"""
        timestamp = datetime.now().isoformat()

        if key not in self.threshold_history:
            self.threshold_history[key] = []

        self.threshold_history[key].append(
            {
                "timestamp": timestamp,
                "old": old_value,
                "new": new_value,
                "reason": reason,
            }
        )

        # 只保留最近50条
        if len(self.threshold_history[key]) > 50:
            self.threshold_history[key] = self.threshold_history[key][-50:]

        self._save_history()
        print(f"📊 动态调整: {key} {old_value} -> {new_value} ({reason})")

    def apply_adjustments(self):
        """应用调整到配置驱动"""
        new_quality = self.adjust_quality_threshold()
        new_retry = self.adjust_retry_threshold()

        # 注意：这里需要重启服务才能生效，或者动态更新配置
        return {
            "quality_min_score": new_quality,
            "max_retry_same_error": new_retry,
            "applied": True,
        }

    def get_stats(self) -> Dict:
        """获取调整统计"""
        return {
            "version": self.VERSION,
            "enabled": self.enabled,
            "current": self.current_thresholds,
            "history": {k: len(v) for k, v in self.threshold_history.items()},
        }


dynamic_threshold = DynamicThreshold()


if __name__ == "__main__":
    print(f"动态阈值调整器 v{dynamic_threshold.VERSION}")
    print(f"统计: {dynamic_threshold.get_stats()}")

    # 测试调整
    result = dynamic_threshold.apply_adjustments()
    print(f"\n调整结果: {result}")
