from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""Butler Cache - Butler Cache 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""私人管家缓存 - Redis 版本（支持多 worker）"""

import os
import pickle
from datetime import timedelta

import redis

# Redis 连接配置
redis_client = redis.Redis(
    host=unified_config.get("redis.host", "localhost"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    decode_responses=False,  # 保持二进制以便 pickle
    socket_connect_timeout=5,
)

# 缓存过期时间（秒）
CACHE_TTL = 3600  # 1小时


def get_butler(user_id: str):
    """获取管家实例（从 Redis 缓存）"""
    from core.agents.builtin.personal_butler_v2 import PersonalButlerV2

    cache_key = f"butler:{user_id}"
    cached = redis_client.get(cache_key)

    if cached:
        try:
            return pickle.loads(cached)
        except Exception as e:
            pass

    # 创建新实例
    butler = PersonalButlerV2(user_id)

    # 存入 Redis
    redis_client.setex(cache_key, CACHE_TTL, pickle.dumps(butler))
    print(f"📦 创建并缓存管家实例: {user_id}")

    return butler


def clear_butler_cache(user_id: str = None):
    """清除缓存"""
    if user_id:
        redis_client.delete(f"butler:{user_id}")
        print(f"🗑️ 清除管家缓存: {user_id}")
    else:
        # 清除所有管家缓存
        keys = redis_client.keys("butler:*")
        if keys:
            redis_client.delete(*keys)
            print(f"🗑️ 清除所有管家缓存 ({len(keys)} 个)")


def get_cache_stats():
    """获取缓存统计"""
    keys = redis_client.keys("butler:*")
    return {"cached_users": len(keys), "keys": [k.decode() for k in keys]}
