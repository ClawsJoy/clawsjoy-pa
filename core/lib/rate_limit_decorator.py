#!/usr/bin/env python3
"""Rate Limit Decorator - Rate Limit Decorator 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""限流装饰器 - 用于任何函数"""
from functools import wraps

from core.lib.rate_limit_manager import rate_limit_manager


def rate_limit(module: str):
    """限流装饰器"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not rate_limit_manager.acquire(module):
                return {"error": "系统繁忙，请稍后重试", "success": False}
            return func(*args, **kwargs)

        return wrapper

    return decorator


def rate_limit_async(module: str):
    """异步限流装饰器"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not rate_limit_manager.acquire(module):
                return {"error": "系统繁忙，请稍后重试", "success": False}
            return await func(*args, **kwargs)

        return wrapper

    return decorator
