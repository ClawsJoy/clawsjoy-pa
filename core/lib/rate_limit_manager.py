#!/usr/bin/env python3
"""Rate Limit Manager - Rate Limit Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""统一限流管理器 - 所有模块共用"""
import threading
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

import yaml


class Priority(Enum):
    SYSTEM = 1
    REGISTERED = 2
    GUEST = 3
    TASK = 4
    LLM = 5


@dataclass
class RateLimitConfig:
    max_requests: int = 20
    time_window: float = 1.0
    queue_size: int = 100
    priority: int = 3


class RateLimiter:
    """单模块限流器"""

    def __init__(self, name: str, config: RateLimitConfig):
        self.name = name
        self.max_requests = config.max_requests
        self.time_window = config.time_window
        self.queue_size = config.queue_size
        self.priority = config.priority
        self.requests = deque()
        self.waiting = deque()
        self.lock = threading.Lock()
        self.stats = {"total": 0, "allowed": 0, "rejected": 0, "queued": 0}

    def acquire(self, timeout: float = None) -> bool:
        """获取许可"""
        with self.lock:
            self.stats["total"] += 1
            now = time.time()

            # 清理过期请求
            while self.requests and now - self.requests[0] > self.time_window:
                self.requests.popleft()

            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                self.stats["allowed"] += 1
                return True

            self.stats["rejected"] += 1
            return False

    def get_stats(self) -> Dict:
        return {
            "name": self.name,
            "max_requests": self.max_requests,
            "time_window": self.time_window,
            "total": self.stats["total"],
            "allowed": self.stats["allowed"],
            "rejected": self.stats["rejected"],
            "current_load": len(self.requests),
        }


class RateLimitManager:
    """统一限流管理器 - 单例"""

    _instance = None
    _limiters: Dict[str, RateLimiter] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_file = Path(__file__).parent.parent / "config/rate_limit.yaml"
        if config_file.exists():
            with open(config_file, "r") as f:
                self.config = unified_config.get("rate_limit_manager", {})
        else:
            self.config = {
                "enabled": True,
                "default": {"max_requests": 20, "time_window": 1},
            }

        self.enabled = self.config.get("enabled", True)
        self.default_config = RateLimitConfig(**self.config.get("default", {}))

    def _get_config(self, module: str) -> RateLimitConfig:
        module_config = self.config.get("modules", {}).get(module, {})
        return RateLimitConfig(
            max_requests=module_config.get(
                "max_requests", self.default_config.max_requests
            ),
            time_window=module_config.get(
                "time_window", self.default_config.time_window
            ),
            queue_size=module_config.get("queue_size", self.default_config.queue_size),
            priority=module_config.get("priority", self.default_config.priority),
        )

    def get_limiter(self, module: str) -> RateLimiter:
        """获取模块限流器"""
        if module not in self._limiters:
            config = self._get_config(module)
            self._limiters[module] = RateLimiter(module, config)
        return self._limiters[module]

    def acquire(self, module: str, timeout: float = None) -> bool:
        """尝试获取许可"""
        if not self.enabled:
            return True
        return self.get_limiter(module).acquire(timeout)

    def get_stats(self, module: str = None) -> Dict:
        """获取统计信息"""
        if module:
            return self.get_limiter(module).get_stats()
        return {name: limiter.get_stats() for name, limiter in self._limiters.items()}

    def reload(self):
        """热重载配置"""
        self._limiters.clear()
        self._load_config()


rate_limit_manager = RateLimitManager()
