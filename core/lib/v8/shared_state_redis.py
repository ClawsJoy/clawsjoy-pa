#!/usr/bin/env python3
"""#17 多实例状态共享(Redis) — 会话状态 + 跨实例锁。

单机版内存状态(如 browser_local._browser_conns 元数据 / 抢占请求)不跨实例共享;
本模块用 Redis 存元数据(连接注册/抢占/通知计数), 供多网关实例读写, Redis 不可用静默降级本地。

设计:
- _shared_redis_enabled: 环境变量 CLAWSJOY_REDIS_SHARED=1 显式开启(默认关, 不改变现有行为)
- 连接元数据: hash key "clawsjoy:shared:conns" → {user_id: {connected_at, tag, state, instance}}
- 抢占请求: hash key "clawsjoy:shared:preempt" → {session_id: [requests]}
- 跨实例锁: SET NX EX(lock 接口)
"""
import json
import os
import time
from typing import Optional

_redis_client = None
_redis_enabled = None


def _get_redis():
    """惰性初始化 Redis 客户端(直连, 不依赖 redis_manager.enabled)"""
    global _redis_client, _redis_enabled
    if _redis_enabled is not None:
        return _redis_client if _redis_enabled else None
    _redis_enabled = os.environ.get("CLAWSJOY_REDIS_SHARED", "0") == "1"
    if not _redis_enabled:
        return None
    try:
        import redis as _r
        _redis_client = _r.Redis(
            host=os.environ.get("CLAWSJOY_REDIS_HOST", "localhost"),
            port=int(os.environ.get("CLAWSJOY_REDIS_PORT", "6379")),
            db=int(os.environ.get("CLAWSJOY_REDIS_DB", "1")),
            decode_responses=True,
        )
        _redis_client.ping()
    except Exception as _e:
        print(f"[SHARED_REDIS] 连接失败, 降级本地: {_e}")
        _redis_enabled = False
        _redis_client = None
    return _redis_client


def shared_enabled() -> bool:
    return _get_redis() is not None


# ===== 连接元数据共享(browser_local._browser_conns) =====
_CONN_HASH = "clawsjoy:shared:conns"


def sync_conn_meta(user_id: str, meta: dict, ttl: int = 3600):
    """跨实例同步连接元数据(connected_at/tag/state/instance)。meta 必须 JSON 可序列化。"""
    _r = _get_redis()
    if _r is None:
        return
    try:
        _key = f"{_CONN_HASH}:{user_id}"
        _r.hset(_key, mapping={k: json.dumps(v, ensure_ascii=False) for k, v in (meta or {}).items()})
        _r.expire(_key, ttl)
    except Exception:
        pass


def get_conn_meta(user_id: str) -> dict:
    """读取跨实例连接元数据(本机无连接时查询远端实例)。"""
    _r = _get_redis()
    if _r is None:
        return {}
    try:
        _raw = _r.hgetall(f"{_CONN_HASH}:{user_id}")
        _out = {}
        for _k, _v in (_raw or {}).items():
            try:
                _out[_k] = json.loads(_v)
            except Exception:
                _out[_k] = _v
        return _out
    except Exception:
        return {}


def clear_conn_meta(user_id: str):
    _r = _get_redis()
    if _r is None:
        return
    try:
        _r.delete(f"{_CONN_HASH}:{user_id}")
    except Exception:
        pass


def list_conn_users() -> list:
    """列出 Redis 中所有已注册连接的 user_id(供远端连接发现)。"""
    _r = _get_redis()
    if _r is None:
        return []
    try:
        _keys = _r.keys(f"{_CONN_HASH}:*")
        return [str(_k).rsplit(":", 1)[-1] for _k in (_keys or [])]
    except Exception:
        return []


# ===== 跨实例锁 =====
def acquire_shared_lock(lock_name: str, ttl: int = 30, wait_timeout: float = 5.0) -> Optional[bool]:
    """跨实例互斥锁(SET NX EX)。返回 True=获取成功; False/None=未获取。"""
    _r = _get_redis()
    if _r is None:
        return True  # Redis 不可用: 单机无竞争, 视为获得
    _key = f"clawsjoy:shared:lock:{lock_name}"
    _deadline = time.time() + wait_timeout
    while time.time() < _deadline:
        try:
            if _r.set(_key, "1", nx=True, ex=ttl):
                return True
        except Exception:
            return True
        time.sleep(0.05)
    return False


def release_shared_lock(lock_name: str):
    _r = _get_redis()
    if _r is None:
        return
    try:
        _r.delete(f"clawsjoy:shared:lock:{lock_name}")
    except Exception:
        pass
