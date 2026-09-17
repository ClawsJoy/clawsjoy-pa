#!/usr/bin/env python3
"""Config Cache - Config Cache 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigCache:
    """配置缓存 - 减少IO和解析开销"""

    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, tuple] = {}  # key -> (value, timestamp)
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                return value
            del self.cache[key]
        return None

    def set(self, key: str, value: Any):
        """设置缓存"""
        self.cache[key] = (value, datetime.now())

    def invalidate(self, pattern: str = None):
        """使缓存失效"""
        if pattern:
            keys_to_remove = [k for k in self.cache if pattern in k]
            for k in keys_to_remove:
                del self.cache[k]
        else:
            self.cache.clear()


config_cache = ConfigCache()
