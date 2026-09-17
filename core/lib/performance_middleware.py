"""性能监控中间件"""

import logging
import time
from functools import wraps

from flask import g, request

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, slow_threshold_ms: int = 1000):
        self.slow_threshold_ms = slow_threshold_ms
        self._request_count = 0
        self._total_duration = 0
        self._slow_count = 0

    def record(self, endpoint: str, duration_ms: float):
        """记录请求性能"""
        self._request_count += 1
        self._total_duration += duration_ms

        if duration_ms > self.slow_threshold_ms:
            self._slow_count += 1
            logger.warning(f"慢请求: {endpoint} - {duration_ms:.0f}ms")

    def get_stats(self) -> dict:
        """获取统计信息"""
        avg_duration = (
            self._total_duration / self._request_count if self._request_count > 0 else 0
        )
        return {
            "total_requests": self._request_count,
            "avg_duration_ms": round(avg_duration, 2),
            "slow_requests": self._slow_count,
            "slow_percentage": (
                round(self._slow_count / self._request_count * 100, 2)
                if self._request_count > 0
                else 0
            ),
            "slow_threshold_ms": self.slow_threshold_ms,
        }


# 全局监控实例
perf_monitor = PerformanceMonitor()


def monitor_performance(f):
    """性能监控装饰器"""

    @wraps(f)
    def wrapped(*args, **kwargs):
        start = time.time()
        try:
            return f(*args, **kwargs)
        finally:
            duration = (time.time() - start) * 1000
            perf_monitor.record(request.path, duration)

    return wrapped


def get_perf_stats():
    """获取性能统计"""
    return perf_monitor.get_stats()
