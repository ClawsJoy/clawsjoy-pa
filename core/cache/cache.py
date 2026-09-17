from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""Cache - Cache 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import hashlib
import json
from typing import Any, Optional

from core.lib.unified_config import unified_config


class RedisCache:
    """Redis 缓存（带 fallback 内存缓存）"""

    def __init__(self):
        self._cache = {}
        self._redis = None
        self._init_redis()

    def _init_redis(self):
        try:
            import redis

            self._redis = redis.Redis(
                host=unified_config.get("redis.host", "localhost"),
                port=unified_config.get("services.\1.port", 6379),
                decode_responses=True,
                socket_connect_timeout=2,
            )
            self._redis.ping()
            print("   ✅ Redis 连接成功")
        except Exception as e:
            print("   ⚠️ Redis 不可用，使用内存缓存")
            self._redis = None

    def _key(self, user_id: str, message: str) -> str:
        content = f"{user_id}:{message}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def get(self, user_id: str, message: str) -> Optional[str]:
        key = self._key(user_id, message)

        if self._redis:
            value = self._redis.get(f"cache:{key}")
            if value:
                return value

        # fallback 到内存
        if key in self._cache:
            cached, ts = self._cache[key]
            import time

            if time.time() - ts < 3600:
                return cached

        return None

    def set(self, user_id: str, message: str, response: str):
        key = self._key(user_id, message)

        if self._redis:
            self._redis.setex(f"cache:{key}", 3600, response)

        # 内存缓存
        import time

        self._cache[key] = (response, time.time())

    def clear(self):
        if self._redis:
            self._redis.flushdb()
        self._cache.clear()


cache = RedisCache()
