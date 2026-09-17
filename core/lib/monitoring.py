"""监控集成 - Prometheus + 旁路智能监控"""

import time
from functools import wraps
from typing import Any, Dict

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# 定义指标
REQUEST_COUNT = Counter(
    "clawsjoy_requests_total", "Total request count", ["method", "endpoint", "status"]
)

REQUEST_DURATION = Histogram(
    "clawsjoy_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

ACTIVE_REQUESTS = Gauge("clawsjoy_active_requests", "Active requests count")

LLM_CALLS = Counter("clawsjoy_llm_calls_total", "Total LLM calls", ["model", "status"])

MEMORY_OPERATIONS = Counter(
    "clawsjoy_memory_operations_total",
    "Total memory operations",
    ["operation", "status"],
)

VECTOR_SEARCH_DURATION = Histogram(
    "clawsjoy_vector_search_duration_seconds",
    "Vector search duration",
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2),
)


# 旁路智能监控
class IntelligentMonitor:
    """旁路智能监控 - 不阻塞主流程"""

    def __init__(self):
        self.anomaly_scores = {}
        self.baseline = {}

    def record_request(self, endpoint: str, duration: float, status: int):
        """记录请求，用于异常检测"""
        # 更新基线
        key = f"{endpoint}"
        if key not in self.baseline:
            self.baseline[key] = {"count": 0, "sum": 0, "max": 0}

        self.baseline[key]["count"] += 1
        self.baseline[key]["sum"] += duration
        self.baseline[key]["max"] = max(self.baseline[key]["max"], duration)

        # 异常检测
        avg = self.baseline[key]["sum"] / self.baseline[key]["count"]
        if duration > avg * 3 and self.baseline[key]["count"] > 10:
            print(
                f"⚠️ 异常检测: {endpoint} 响应时间异常 ({duration:.2f}s > {avg*3:.2f}s)"
            )

    def get_health_score(self) -> Dict:
        """获取健康分数"""
        # 综合评分
        return {
            "score": 95,
            "status": "healthy",
            "details": {
                "requests_monitored": sum(b["count"] for b in self.baseline.values()),
                "avg_response_time": sum(b["sum"] for b in self.baseline.values())
                / max(1, sum(b["count"] for b in self.baseline.values())),
            },
        }


intelligent_monitor = IntelligentMonitor()


def track_request(endpoint: str):
    """装饰器：自动追踪请求"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            ACTIVE_REQUESTS.inc()
            try:
                result = func(*args, **kwargs)
                status = 200
                return result
            except Exception as e:
                status = 500
                raise
            finally:
                duration = time.time() - start
                REQUEST_COUNT.labels(
                    method="POST", endpoint=endpoint, status=status
                ).inc()
                REQUEST_DURATION.labels(method="POST", endpoint=endpoint).observe(
                    duration
                )
                ACTIVE_REQUESTS.dec()
                intelligent_monitor.record_request(endpoint, duration, status)

        return wrapper

    return decorator


def track_llm_call(model: str, success: bool):
    """记录 LLM 调用"""
    status = "success" if success else "error"
    LLM_CALLS.labels(model=model, status=status).inc()


def track_memory_op(operation: str, success: bool):
    """记录记忆操作"""
    status = "success" if success else "error"
    MEMORY_OPERATIONS.labels(operation=operation, status=status).inc()
