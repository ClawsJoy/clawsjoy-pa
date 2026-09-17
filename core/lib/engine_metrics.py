"""引擎性能指标"""

import threading
import time
from collections import defaultdict
from datetime import datetime


class EngineMetrics:
    """引擎指标收集器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.metrics = defaultdict(
            lambda: {
                "total": 0,
                "success": 0,
                "total_latency": 0,
                "errors": 0,
                "last_error": None,
            }
        )
        self._lock = threading.Lock()

    def record(self, engine: str, success: bool, latency_ms: float, error: str = None):
        """记录一次调用"""
        with self._lock:
            self.metrics[engine]["total"] += 1
            self.metrics[engine]["total_latency"] += latency_ms
            if success:
                self.metrics[engine]["success"] += 1
            else:
                self.metrics[engine]["errors"] += 1
                if error:
                    self.metrics[engine]["last_error"] = error

    def get_summary(self) -> dict:
        """获取摘要"""
        summary = {}
        for engine, data in self.metrics.items():
            total = data["total"]
            success_rate = (data["success"] / total * 100) if total > 0 else 0
            avg_latency = (data["total_latency"] / total) if total > 0 else 0
            summary[engine] = {
                "total": total,
                "success_rate": round(success_rate, 2),
                "avg_latency_ms": round(avg_latency, 2),
                "errors": data["errors"],
                "last_error": data["last_error"],
            }
        return summary

    def reset(self):
        with self._lock:
            self.metrics.clear()


engine_metrics = EngineMetrics()
