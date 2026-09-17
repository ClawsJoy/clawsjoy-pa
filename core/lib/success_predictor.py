#!/usr/bin/env python3
"""Success Predictor - Success Predictor 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""成功率预测器 v1.0.02 - 适配实际日志格式"""

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.lib.unified_config import unified_config


class SuccessPredictor:
    """成功率预测器 - 基于历史数据预测任务成功率"""

    VERSION = "1.0.02"

    def __init__(self):
        self.root = unified_config.ROOT
        from pathlib import Path

        self.log_file = Path(self.root) / "logs" / "active_runner.log"
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

        current_task = None

        for line in lines:
            # 匹配执行行: [数字] 执行: 任务名
            if "执行:" in line:
                # 提取任务名
                match = re.search(r"执行:\s*(.+?)(?:\s*\(|$)", line)
                if match:
                    current_task = match.group(1).strip()
                    # 移除可能的前缀
                    current_task = re.sub(r"^\[.*?\]\s*", "", current_task)

            # 匹配完成
            elif "✅ 完成" in line and current_task:
                self._task_history[current_task]["success"] += 1
                self._task_history[current_task]["recent"].append(
                    ("success", datetime.now())
                )
                current_task = None

            # 匹配失败
            elif "❌ 失败" in line and current_task:
                self._task_history[current_task]["fail"] += 1
                self._task_history[current_task]["recent"].append(
                    ("fail", datetime.now())
                )
                current_task = None

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

        # 精确匹配
        history = self._task_history.get(task_name)

        # 模糊匹配
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

        # 趋势
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
            "enabled": True,
        }

    def reload(self):
        """重新加载"""
        self._task_history = None
        self._load_history()


success_predictor = SuccessPredictor()


if __name__ == "__main__":
    print(f"成功率预测器 v{success_predictor.VERSION}")
    stats = success_predictor.get_stats()
    print(f"统计: 跟踪 {stats['total_tasks_tracked']} 个任务")

    if stats["total_tasks_tracked"] > 0:
        print("\n最佳任务:")
        for task in success_predictor.get_best_tasks(5):
            print(f"  ✅ {task['task'][:40]}: {task['rate']*100:.0f}%")

        print("\n待优化任务:")
        for task in success_predictor.get_worst_tasks(5):
            print(f"  ⚠️ {task['task'][:40]}: {task['rate']*100:.0f}%")
