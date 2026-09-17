"""响应缓存 - 减少重复 LLM 调用"""

import hashlib
import logging
import time
from collections import OrderedDict

logger = logging.getLogger(__name__)


class ResponseCache:
    """LRU 缓存 + TTL 过期"""

    def __init__(self, max_size: int = 500, ttl: int = 1800):
        """
        Args:
            max_size: 最大缓存条目数
            ttl: 缓存过期时间（秒），默认30分钟
        """
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
        self._hit_count = 0
        self._miss_count = 0

    def _make_key(self, user_id: str, message: str) -> str:
        """生成缓存键"""
        content = f"{user_id}:{message}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, user_id: str, message: str):
        """获取缓存"""
        key = self._make_key(user_id, message)
        # 优先使用 Redis
        if redis_cache.enabled:
            value = redis_cache.get(key)
            if value is not None:
                self._hit_count += 1
                return value
            self._miss_count += 1
            return None
        # 降级到内存缓存
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                self.cache.move_to_end(key)
                self._hit_count += 1
                return value
            else:
                del self.cache[key]
        self._miss_count += 1
        return None

    def set(self, user_id: str, message: str, value):
        """设置缓存"""
        key = self._make_key(user_id, message)
        # 优先使用 Redis
        if redis_cache.enabled:
            redis_cache.set(key, value, ttl=self.ttl)
        else:
            self.cache[key] = (value, time.time())
            self.cache.move_to_end(key)

        # 限制缓存大小
        while len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
        logger.debug(f"缓存已设置: {message[:30]}...")

    def get_stats(self) -> dict:
        """获取缓存统计"""
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "hit_rate": f"{hit_rate * 100:.1f}%",
        }

    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self._hit_count = 0
        self._miss_count = 0
        logger.info("缓存已清空")


# 全局缓存实例
response_cache = ResponseCache()

# 优先使用 Redis 缓存
try:
    from core.lib.redis_cache import redis_cache
    _cache_backend = redis_cache
except:
    _cache_backend = None
