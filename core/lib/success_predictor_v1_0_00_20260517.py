#!/usr/bin/env python3
"""Success Predictor V1 0 00 20260517 - Success Predictor V1 0 00 20260517 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""成功率预测器 v1.0.00 - 基于历史数据预测任务成功率"""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.lib.config_driver import config_driver
from core.lib.unified_config import unified_config


class SuccessPredictor:
    """成功率预测器 - 预测任务成功概率"""

    VERSION = "1.0.00"

    def __init__(self):
        self.root = unified_config.ROOT
        self.log_file = self.root / "logs" / "active_runner.log"
        self.history_window = config_driver.get("optimization.history_window_size", 100)
        self._task_history = None
        self._skill_history = None

    def _load_history(self):
        """加载历史数据"""
        if not self.log_file.exists():
            return

        content = self.log_file.read_text(encoding="utf-8", errors="ignore")
        lines = content.strip().split("\n")

        task_history = defaultdict(lambda: {"success": 0, "fail": 0, "recent": []})
        skill_history = defaultdict(lambda: {"success": 0, "fail": 0})

        for line in lines[-self.history_window * 2 :]:
            # 解析任务
            if "[执行]" in line:
                # 提取任务名
                import re

                match = re.search(r"执行: (.*?)(?:\(|$)", line)
                if match:
                    task_name = match.group(1).strip()

                    # 判断成功/失败
                    if "✅ 完成" in line:
                        task_history[task_name]["success"] += 1
                        task_history[task_name]["recent"].append(
                            ("success", datetime.now())
                        )
                    elif "❌ 失败" in line:
                        task_history[task_name]["fail"] += 1
                        task_history[task_name]["recent"].append(
                            ("fail", datetime.now())
                        )

                    # 限制最近记录数量
                    if len(task_history[task_name]["recent"]) > 20:
                        task_history[task_name]["recent"] = task_history[task_name][
                            "recent"
                        ][-20:]

        self._task_history = task_history
        self._skill_history = skill_history

    def predict_task_success_rate(self, task_name: str) -> Dict:
        """预测单个任务的成功率"""
        if self._task_history is None:
            self._load_history()

        history = self._task_history.get(
            task_name, {"success": 0, "fail": 0, "recent": []}
        )
        total = history["success"] + history["fail"]

        if total == 0:
            # 无历史数据，使用默认值
            return {
                "task": task_name,
                "predicted_rate": 0.5,
                "confidence": 0.2,
                "total_samples": 0,
                "trend": "unknown",
            }

        rate = history["success"] / total

        # 计算趋势（基于最近5次）
        recent = history["recent"][-5:]
        recent_success = sum(1 for r in recent if r[0] == "success")
        recent_rate = recent_success / len(recent) if recent else rate

        if recent_rate > rate + 0.1:
            trend = "improving"
        elif recent_rate < rate - 0.1:
            trend = "declining"
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

    def predict_skill_success_rate(self, skill_name: str) -> Dict:
        """预测技能的成功率"""
        if self._skill_history is None:
            self._load_history()

        history = self._skill_history.get(skill_name, {"success": 0, "fail": 0})
        total = history["success"] + history["fail"]

        if total == 0:
            return {
                "skill": skill_name,
                "predicted_rate": 0.5,
                "confidence": 0.2,
                "total_samples": 0,
            }

        rate = history["success"] / total
        confidence = min(0.95, 0.3 + total / 200)

        return {
            "skill": skill_name,
            "predicted_rate": round(rate, 2),
            "confidence": round(confidence, 2),
            "total_samples": total,
        }

    def get_best_tasks(self, limit: int = 10) -> List[Dict]:
        """获取预测成功率最高的任务"""
        if self._task_history is None:
            self._load_history()

        results = []
        for task_name, history in self._task_history.items():
            total = history["success"] + history["fail"]
            if total >= 3:  # 至少有3次尝试
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
            if total >= 3:
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


success_predictor = SuccessPredictor()


if __name__ == "__main__":
    print(f"成功率预测器 v{success_predictor.VERSION}")
    print(f"统计: {success_predictor.get_stats()}")

    # 显示最佳任务
    print("\n最佳任务预测:")
    for task in success_predictor.get_best_tasks(5):
        print(f"  {task['task']}: {task['rate']*100:.0f}% ({task['samples']}次)")

    # 显示最差任务
    print("\n最差任务预测:")
    for task in success_predictor.get_worst_tasks(5):
        print(f"  {task['task']}: {task['rate']*100:.0f}% ({task['samples']}次)")
