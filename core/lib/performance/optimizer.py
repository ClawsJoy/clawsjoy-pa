"""性能优化模块 - 缓存、批处理、内存优化"""

import time
import json
import hashlib
from typing import Dict, List, Any, Optional, Callable
from collections import OrderedDict
from functools import wraps
import threading


class CacheManager:
    """缓存管理器 - LRU + TTL"""
    
    def __init__(self, max_size: int = 100, ttl: int = 300):
        self._cache = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl  # 秒
        self._stats = {"hits": 0, "misses": 0}
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                self._cache.move_to_end(key)
                self._stats["hits"] += 1
                return value
            else:
                del self._cache[key]
        
        self._stats["misses"] += 1
        return None
    
    def set(self, key: str, value: Any):
        """设置缓存"""
        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
        
        self._cache[key] = (value, time.time())
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
    
    def invalidate(self, key_prefix: str):
        """精准失效：删除匹配前缀的缓存"""
        keys = [k for k in self._cache if k.startswith(key_prefix)]
        for k in keys:
            del self._cache[k]
        return len(keys)
    
    def get_stats(self) -> Dict:
        """获取统计"""
        total = self._stats["hits"] + self._stats["misses"]
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hit_rate": self._stats["hits"] / total if total > 0 else 0,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"]
        }


class BatchProcessor:
    """批处理器"""
    
    def __init__(self, batch_size: int = 8, flush_interval: float = 1.0):
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._queue = []
        self._lock = threading.Lock()
        self._last_flush = time.time()
    
    def add(self, item: Any, callback: Callable = None):
        """添加任务到批处理队列"""
        with self._lock:
            self._queue.append({"item": item, "callback": callback})
            
            if len(self._queue) >= self._batch_size:
                self._flush()
    
    def _flush(self):
        """处理批处理队列"""
        if not self._queue:
            return
        
        batch = self._queue[:self._batch_size]
        self._queue = self._queue[self._batch_size:]
        
        # 处理批次
        for item in batch:
            if item["callback"]:
                # 异步回调
                threading.Thread(target=item["callback"], args=(item["item"],), daemon=True).start()
    
    def flush(self):
        """强制刷新"""
        self._flush()


class ModelSelector:
    """模型选择器 - 根据任务复杂度选择模型"""
    
    def __init__(self):
        self._model_scores = {
            "qwen2.5:1.5b": {"speed": 100, "accuracy": 60, "memory": 1.5},
            "qwen2.5:7b-instruct-q4_0-gpu": {"speed": 80, "accuracy": 75, "memory": 2.5},
            "phi3:mini": {"speed": 70, "accuracy": 85, "memory": 3.0},
            "codellama:7b": {"speed": 50, "accuracy": 88, "memory": 3.8},
            "qwen2.5:7b-instruct-q4_0-gpu": {"speed": 40, "accuracy": 90, "memory": 4.7},
        }
    
    def select(self, task: str, input_length: int = 0) -> str:
        """选择最适合的模型"""
        task_lower = task.lower()
        
        # 科学计算用大模型
        if any(kw in task_lower for kw in ["sqrt", "sin", "cos", "log", "函数"]):
            return "qwen2.5:7b-instruct-q4_0-gpu"
        
        # 代码任务
        if any(kw in task_lower for kw in ["代码", "编程", "写一个"]):
            return "codellama:7b"
        
        # 长文本用 phi3
        if input_length > 100:
            return "phi3:mini"
        
        # 默认用小模型
        if input_length < 30:
            return "qwen2.5:7b-instruct-q4_0-gpu"
        
        return "phi3:mini"


# 全局实例
cache_manager = CacheManager(max_size=200, ttl=600)
batch_processor = BatchProcessor(batch_size=8)
model_selector = ModelSelector()
