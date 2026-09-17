#!/usr/bin/env python3
"""Success Predictor V1 0 01 20260517 - Success Predictor V1 0 01 20260517 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""成功率预测器 v1.0.01 - 修复日志解析"""

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.lib.config_driver import config_driver
from core.lib.unified_config import unified_config


class SuccessPredictor:
    """成功率预测器 - 基于历史数据预测任务成功率"""

    VERSION = "1.0.01"

    def __init__(self):
        self.root = unified_config.ROOT
        self.log_file = self.root / "logs" / "active_runner.log"
        self.history_window = config_driver.get(
            "optimization.history_window_size", 1000
        )
        self._task_history = None
        self._load_history()

    def _load_history(self):
        """从日志加载历史数据"""
        self._task_history = defaultdict(
            lambda: {"success": 0, "fail": 0, "recent": []}
        )

        if not self.log_file.exists():
            print(f"日志文件不存在: {self.log_file}")
            return

        content = self.log_file.read_text(encoding="utf-8", errors="ignore")
        lines = content.strip().split("\n")

        # 从后往前解析，只取最近的窗口大小
        for line in lines[-self.history_window :]:
            # 匹配执行行
            if "[执行]" in line:
                # 提取任务名（多种格式）
                patterns = [
                    r"执行: (.*?)\s*\(",  # 带优先级
                    r"执行: (.*?)$",  # 不带优先级
                    r"制作视频: (.*?)$",  # 制作视频格式
                ]

                task_name = None
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        task_name = match.group(1).strip()
                        break

                if task_name:
                    # 判断成功/失败
                    if "✅ 完成" in line:
                        self._task_history[task_name]["success"] += 1
                        self._task_history[task_name]["recent"].append(
                            ("success", datetime.now())
                        )
                    elif "❌ 失败" in line:
                        self._task_history[task_name]["fail"] += 1
                        self._task_history[task_name]["recent"].append(
                            ("fail", datetime.now())
                        )

        # 限制最近记录数量
        for task in self._task_history:
            if len(self._task_history[task]["recent"]) > 20:
                self._task_history[task]["recent"] = self._task_history[task]["recent"][
                    -20:
                ]

        print(f"📊 已加载 {len(self._task_history)} 个任务的历史数据")

    def predict_task_success_rate(self, task_name: str) -> Dict:
        """预测单个任务的成功率"""
        if self._task_history is None:
            self._load_history()

        # 尝试精确匹配
        history = self._task_history.get(task_name)

        # 如果没有精确匹配，尝试模糊匹配
        if not history:
            for name, hist in self._task_history.items():
                if task_name in name or name in task_name:
                    history = hist
                    break

        if not history:
            return {
                "task": task_name,
                "predicted_rate": 0.5,
                "confidence": 0.2,
                "total_samples": 0,
                "trend": "unknown",
            }

        total = history["success"] + history["fail"]
        rate = history["success"] / total if total > 0 else 0.5

        # 计算趋势（基于最近5次）
        recent = history["recent"][-5:]
        if recent:
            recent_success = sum(1 for r in recent if r[0] == "success")
            recent_rate = recent_success / len(recent)

            if recent_rate > rate + 0.1:
                trend = "improving"
            elif recent_rate < rate - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # 置信度（样本越多置信度越高）
        confidence = min(0.95, 0.3 + total / 100)

        return {
            "task": task_name,
            "predicted_rate": round(rate, 2),
            "confidence": round(confidence, 2),
            "total_samples": total,
            "trend": trend,
            "success_count": history["success"],
            "fail_count": history["fail"],
        }

    def get_best_tasks(self, limit: int = 10) -> List[Dict]:
        """获取预测成功率最高的任务"""
        if self._task_history is None:
            self._load_history()

        results = []
        for task_name, history in self._task_history.items():
            total = history["success"] + history["fail"]
            if total >= 2:
                rate = history["success"] / total
                results.append(
                    {"task": task_name, "rate": round(rate, 2), "samples": total}
                )

        results.sort(key=lambda x: x["rate"], reverse=True)
        return results[:limit]

    def get_worst_tasks(self, limit: int = 10) -> List[Dict]:
        """获取预测成功率最低的任务"""
        if self._task_history is None:
            self._load_history()

        results = []
        for task_name, history in self._task_history.items():
            total = history["success"] + history["fail"]
            if total >= 2:
                rate = history["success"] / total
                results.append(
                    {"task": task_name, "rate": round(rate, 2), "samples": total}
                )

        results.sort(key=lambda x: x["rate"])
        return results[:limit]

    def get_stats(self) -> Dict:
        """获取预测器统计"""
        if self._task_history is None:
            self._load_history()

        return {
            "version": self.VERSION,
            "total_tasks_tracked": len(self._task_history) if self._task_history else 0,
            "history_window": self.history_window,
            "enabled": True,
        }

    def reload(self):
        """重新加载历史数据"""
        self._task_history = None
        self._load_history()


success_predictor = SuccessPredictor()


if __name__ == "__main__":
    print(f"成功率预测器 v{success_predictor.VERSION}")
    stats = success_predictor.get_stats()
    print(f"统计: 跟踪 {stats['total_tasks_tracked']} 个任务")

    print("\n最佳任务预测:")
    for task in success_predictor.get_best_tasks(5):
        print(f"  {task['task'][:40]}: {task['rate']*100:.0f}% ({task['samples']}次)")

    print("\n最差任务预测:")
    for task in success_predictor.get_worst_tasks(5):
        print(f"  {task['task'][:40]}: {task['rate']*100:.0f}% ({task['samples']}次)")
