#!/usr/bin/env python3
"""Gray Executor - Gray Executor 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""灰度执行器 - 配置驱动"""
import random
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, Optional

from core.lib.closed_loop_config import closed_loop_config


class GrayExecutor:
    """灰度执行器"""

    def __init__(self):
        self._load_config()
        self._samples = deque(maxlen=100)
        self._gray_metrics = {}

    def _load_config(self):
        self.enabled = closed_loop_config.get("gray.enabled", True)
        self.percentage = closed_loop_config.get("gray.percentage", 20)
        self.monitoring_time = closed_loop_config.get("gray.monitoring_time", 60)
        self.success_threshold = closed_loop_config.get("gray.success_threshold", 0.95)
        self.sample_size = closed_loop_config.get("gray.sample_size", 10)

    def should_use_gray(self, suggestion: str, risk_level: str) -> bool:
        """判断是否使用灰度"""
        if not self.enabled:
            return False
        gray_levels = closed_loop_config.get(
            "execution.gray_execute_levels", ["medium"]
        )
        if risk_level not in gray_levels:
            return False
        # 随机决定是否灰度
        return random.randint(1, 100) <= self.percentage

    def execute_gray(self, suggestion: str, executor) -> Dict:
        """灰度执行"""
        start_time = time.time()
        result = executor(suggestion)
        execution_time = time.time() - start_time

        # 记录样本
        self._samples.append(
            {
                "timestamp": datetime.now().isoformat(),
                "suggestion": suggestion,
                "success": result.get("success", False),
                "execution_time": execution_time,
            }
        )

        # 评估是否需要回滚
        need_rollback = self._evaluate_rollback()

        return {
            "executed": True,
            "result": result,
            "gray": True,
            "sample_count": len(self._samples),
            "need_rollback": need_rollback,
        }

    def _evaluate_rollback(self) -> bool:
        """评估是否需要回滚"""
        if len(self._samples) < self.sample_size:
            return False

        recent = list(self._samples)[-self.sample_size :]
        success_count = sum(1 for s in recent if s.get("success", False))
        success_rate = success_count / len(recent)

        return success_rate < self.success_threshold

    def get_status(self) -> Dict:
        """获取灰度状态"""
        return {
            "enabled": self.enabled,
            "percentage": self.percentage,
            "samples": len(self._samples),
            "sample_size": self.sample_size,
            "success_rate": sum(1 for s in self._samples if s.get("success"))
            / max(1, len(self._samples)),
        }


gray_executor = GrayExecutor()
