"""独立缓存模块 - 无任何外部依赖"""

import time
from threading import Lock

class StandaloneCache:
    """独立内存缓存"""
    
    def __init__(self, ttl: int = 300, max_size: int = 500):
        self.ttl = ttl
        self.max_size = max_size
        self._cache = {}
        self._lock = Lock()
    
    def get(self, key: str):
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl:
                    return value
                else:
                    del self._cache[key]
            return None
    
    def set(self, key: str, value: str):
        with self._lock:
            self._cache[key] = (value, time.time())
            # 简单限制大小
            if len(self._cache) > self.max_size:
                oldest = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest]
    
    def clear(self):
        with self._lock:
            self._cache.clear()
    
    def size(self):
        return len(self._cache)

# 单例实例
cache = StandaloneCache()
