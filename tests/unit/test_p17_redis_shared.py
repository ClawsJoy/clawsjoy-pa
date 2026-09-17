"""#17 多实例状态共享(Redis)回归测试: 连接元数据同步 + 跨实例锁 + 远端回退"""
import json
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _redis_on(monkeypatch):
    """开启 Redis 共享(用 fake client 隔离真实 Redis)"""
    import core.lib.v8.shared_state_redis as sr

    # 构造 fake redis: 内存 dict 模拟 hset/hgetall/delete/expire/set(nx)/ping
    class FakeRedis:
        def __init__(self):
            self._hash = {}
            self._keys = {}

        def ping(self):
            return True

        def hset(self, key, mapping=None):
            self._hash.setdefault(key, {}).update(mapping or {})
            return 1

        def hgetall(self, key):
            return dict(self._hash.get(key, {}))

        def delete(self, *keys):
            for k in keys:
                self._hash.pop(k, None)
                self._keys.pop(k, None)
            return 1

        def expire(self, key, ttl):
            return True

        def set(self, key, val, nx=False, ex=None):
            if nx and key in self._keys:
                return False
            self._keys[key] = val
            return True

        def keys(self, pattern=""):
            prefix = pattern.rstrip("*")
            return [k for k in self._hash if k.startswith(prefix)]

    _fake = FakeRedis()
    monkeypatch.setattr(sr, "_redis_client", _fake)
    monkeypatch.setattr(sr, "_redis_enabled", True)
    yield _fake
    monkeypatch.setattr(sr, "_redis_enabled", None)


def test_sync_and_get_conn_meta(_redis_on):
    """连接元数据写入 Redis → 可读回(跨实例发现)"""
    import core.lib.v8.shared_state_redis as sr

    sr.sync_conn_meta(
        "user_a",
        {"connected_at": 1000, "tag": "python-client", "state": {"state": "connected", "url": ""}, "instance": "gw1"},
    )
    meta = sr.get_conn_meta("user_a")
    assert meta.get("tag") == "python-client"
    assert meta.get("state", {}).get("state") == "connected"
    assert meta.get("instance") == "gw1"
    assert "user_a" in sr.list_conn_users()


def test_clear_conn_meta(_redis_on):
    """断线 → 清除远端元数据"""
    import core.lib.v8.shared_state_redis as sr

    sr.sync_conn_meta("user_b", {"tag": "ext", "state": {"state": "connected"}})
    assert sr.get_conn_meta("user_b").get("tag") == "ext"
    sr.clear_conn_meta("user_b")
    assert sr.get_conn_meta("user_b") == {}


def test_shared_lock_acquire_release(_redis_on):
    """跨实例锁: 获取 → 第二个实例拿不到 → 释放后可拿"""
    import core.lib.v8.shared_state_redis as sr

    assert sr.acquire_shared_lock("test_lock", ttl=30) is True
    assert sr.acquire_shared_lock("test_lock", ttl=30, wait_timeout=0.2) is False, "未释放时应拿不到"
    sr.release_shared_lock("test_lock")
    assert sr.acquire_shared_lock("test_lock", ttl=30) is True, "释放后应可再次获取"
    sr.release_shared_lock("test_lock")


def test_shared_disabled_fallback(monkeypatch):
    """Redis 未启用(环境变量未设) → 降级本地: 读写 no-op, 锁视为获得"""
    import core.lib.v8.shared_state_redis as sr

    monkeypatch.setattr(sr, "_redis_enabled", False)
    monkeypatch.setattr(sr, "_redis_client", None)
    sr.sync_conn_meta("user_x", {"tag": "t"})  # 不应抛
    assert sr.get_conn_meta("user_x") == {}
    assert sr.acquire_shared_lock("any") is True  # 单机视为获得
    sr.release_shared_lock("any")


def test_browser_local_sync_hooks():
    """browser_local 接入点: register/unregister 同步 Redis 元数据"""
    _SRC = open("core/lib/v8/browser_local.py", encoding="utf-8").read()
    assert "sync_conn_meta" in _SRC, "register_ws_connection 应同步元数据"
    assert "clear_conn_meta" in _SRC, "unregister_ws_connection 应清除元数据"
    assert "shared_state_redis" in _SRC, "应引入 shared_state_redis"


def test_browser_local_remote_fallback(monkeypatch):
    """_resolve_conn_user: 本机无连接 + 远端 Redis 有 connected 元数据 → 判定已连接"""
    import core.lib.v8.browser_local as bl
    from core.lib.v8 import shared_state_redis as sr

    class FakeRedis:
        def __init__(self):
            self._h = {}
            self._k = {}

        def ping(self):
            return True

        def hset(self, k, mapping=None):
            self._h.setdefault(k, {}).update(mapping or {})
            return 1

        def hgetall(self, k):
            return dict(self._h.get(k, {}))

        def delete(self, *ks):
            for k in ks:
                self._h.pop(k, None)
                self._k.pop(k, None)
            return 1

        def expire(self, k, ttl):
            return True

        def set(self, k, v, nx=False, ex=None):
            if nx and k in self._k:
                return False
            self._k[k] = v
            return True

        def keys(self, p=""):
            return [k for k in self._h if k.startswith(p.rstrip("*"))]

    monkeypatch.setattr(sr, "_redis_client", FakeRedis())
    monkeypatch.setattr(sr, "_redis_enabled", True)
    # 本机连接表为空 + Redis 有 user_remote 的 connected 元数据
    with bl._browser_lock:
        bl._browser_conns.clear()
    sr.sync_conn_meta("user_remote", {"tag": "python-client", "state": {"state": "connected", "url": ""}})
    assert bl._resolve_conn_user("user_remote") == "user_remote", "远端 connected 应判定已连接"
    # 远端 state 非 connected → 不算
    sr.sync_conn_meta("user_remote", {"tag": "x", "state": {"state": "disconnected"}})
    assert bl._resolve_conn_user("user_remote") is None
