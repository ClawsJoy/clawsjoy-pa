"""请求限流器 - 防止过载"""

import time
from collections import defaultdict
from functools import wraps

from flask import jsonify, request


class RateLimiter:
    """滑动窗口限流器"""

    def __init__(self, default_limit: int = 60, default_window: int = 60):
        """
        Args:
            default_limit: 默认限制次数
            default_window: 时间窗口（秒）
        """
        self.default_limit = default_limit
        self.default_window = default_window
        self._requests = defaultdict(list)

    def _get_key(self, user_id: str = None) -> str:
        """获取限流键"""
        if user_id:
            return f"user:{user_id}"
        return f"ip:{request.remote_addr}"

    def _clean_expired(self, key: str, window: int):
        """清理过期记录"""
        now = time.time()
        cutoff = now - window
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    def is_allowed(
        self, user_id: str = None, limit: int = None, window: int = None
    ) -> tuple:
        """检查是否允许请求"""
        limit = limit or self.default_limit
        window = window or self.default_window
        key = self._get_key(user_id)

        self._clean_expired(key, window)

        if len(self._requests[key]) >= limit:
            return False, len(self._requests[key]), limit

        self._requests[key].append(time.time())
        return True, len(self._requests[key]), limit

    def get_stats(self, user_id: str = None) -> dict:
        """获取限流统计"""
        key = self._get_key(user_id)
        return {
            "current_requests": len(self._requests[key]),
            "limit": self.default_limit,
            "window_seconds": self.default_window,
        }


# 全局限流器实例
rate_limiter = RateLimiter(default_limit=60, default_window=60)


def rate_limit(limit: int = None, window: int = None):
    """速率限制装饰器"""

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            allowed, current, max_limit = rate_limiter.is_allowed(
                limit=limit, window=window
            )
            if not allowed:
                return (
                    jsonify(
                        {
                            "error": "Rate Limit Exceeded",
                            "message": f"请求过于频繁，请稍后再试。当前 {current}/{max_limit}",
                            "retry_after": window or 60,
                        }
                    ),
                    429,
                )
            return f(*args, **kwargs)

        return wrapped

    return decorator
