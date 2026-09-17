"""指标收集 - 全链路监控"""

import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self.timings = defaultdict(list)
        self._lock = threading.Lock()

    def increment(self, name: str, value: int = 1, tags: Dict = None):
        """增加计数器"""
        with self._lock:
            self.counters[name] += value

    def gauge(self, name: str, value: float, tags: Dict = None):
        """设置仪表值"""
        with self._lock:
            self.gauges[name] = value

    def timing(self, name: str, duration_ms: float, tags: Dict = None):
        """记录耗时"""
        with self._lock:
            self.timings[name].append(duration_ms)
            if len(self.timings[name]) > 1000:
                self.timings[name] = self.timings[name][-1000:]

    def record(self, name: str, value: float):
        """记录指标"""
        self.histograms[name].append(value)
        if len(self.histograms[name]) > 1000:
            self.histograms[name] = self.histograms[name][-1000:]

    def get_stats(self) -> Dict:
        """获取统计"""
        with self._lock:
            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "timings": {
                    name: {
                        "count": len(values),
                        "avg": sum(values) / len(values) if values else 0,
                        "max": max(values) if values else 0,
                        "min": min(values) if values else 0,
                    }
                    for name, values in self.timings.items()
                },
            }

    def reset(self):
        """重置指标"""
        with self._lock:
            self.counters.clear()
            self.gauges.clear()
            self.timings.clear()
            self.histograms.clear()


metrics = MetricsCollector()
