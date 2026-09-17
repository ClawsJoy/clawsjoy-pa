"""Redis 缓存适配器"""

import json
import redis
from typing import Optional, Any
from core.lib.unified_config import unified_config


class RedisCache:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        try:
            self.client = redis.Redis(
                host=unified_config.get("redis.host", "localhost"),
                port=unified_config.get("redis.port", 6379),
                db=unified_config.get("redis.db", 0),
                decode_responses=True,
                socket_connect_timeout=2
            )
            self.client.ping()
            self.enabled = True
            print("✅ Redis 缓存已启用")
        except Exception as e:
            print(f"⚠️ Redis 连接失败，使用内存缓存: {e}")
            self.enabled = False
            self._memory_cache = {}
    
    def get(self, key: str) -> Optional[Any]:
        if self.enabled:
            data = self.client.get(key)
            return json.loads(data) if data else None
        return self._memory_cache.get(key)
    
    def set(self, key: str, value: Any, ttl: int = 300):
        if self.enabled:
            self.client.setex(key, ttl, json.dumps(value))
        else:
            self._memory_cache[key] = value
    
    def delete(self, key: str):
        if self.enabled:
            self.client.delete(key)
        elif key in self._memory_cache:
            del self._memory_cache[key]


redis_cache = RedisCache()
