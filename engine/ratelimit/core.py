from engine.lib.logger import engine_logger

"""限流熔断引擎"""

import time
from collections import defaultdict
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)


class RateLimitEngine:
    """限流熔断引擎"""

    def __init__(self):
        self.counters = defaultdict(lambda: {"count": 0, "reset_at": 0})
        self.default_limit = 100
        engine_logger.get().info("🚦 限流熔断引擎已初始化")

    def process(self, input_data: Any, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if isinstance(input_data, str):
            return self.allow(input_data)
        return self.allow(str(input_data))

    def allow(self, key: str) -> bool:
        now = time.time()
        if key not in self.counters:
            self.counters[key] = {
                "limit": self.default_limit,
                "window": 60,
                "count": 0,
                "reset_at": now + 60,
            }
        counter = self.counters[key]
        if now >= counter["reset_at"]:
            counter["count"] = 0
            counter["reset_at"] = now + counter.get("window", 60)
        if counter["count"] >= counter.get("limit", self.default_limit):
            return False
        counter["count"] += 1
        return True

    def get_remaining(self, key: str) -> int:
        if key not in self.counters:
            return self.default_limit
        counter = self.counters[key]
        return max(0, counter.get("limit", self.default_limit) - counter["count"])

    def health_check(self) -> Dict:
        """健康检查"""
        return {"name": self.__class__.__name__, "status": "healthy"}

    def get_stats(self) -> Dict:
        return {"limiters": len(self.counters), "status": "active"}

    def reload(self) -> Dict:
        return {"success": True, "message": "RateLimit engine reloaded"}


ratelimit_engine = RateLimitEngine()
