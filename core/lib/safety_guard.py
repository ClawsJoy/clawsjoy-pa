# core/lib/safety_guard.py
"""安全保护模块"""

import functools
import sys
from typing import Any, Callable

# 设置全局递归深度限制
DEFAULT_RECURSION_LIMIT = 10000
MAX_SAFE_RECURSION = 5000


def set_safe_recursion_limit(limit: int = MAX_SAFE_RECURSION):
    """设置安全的递归深度限制"""
    current_limit = sys.getrecursionlimit()
    if current_limit > limit:
        sys.setrecursionlimit(limit)
        print(f"🔒 递归深度限制已设置为 {limit}")
    return sys.getrecursionlimit()


def safe_recursive(max_depth: int = 1000):
    """递归函数装饰器，防止无限递归"""

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, depth: int = 0, **kwargs):
            if depth > max_depth:
                raise RecursionError(f"递归深度超过限制 {max_depth}")
            return func(*args, depth=depth + 1, **kwargs)

        return wrapper

    return decorator


# 初始化安全限制
set_safe_recursion_limit()
