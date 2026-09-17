#!/usr/bin/env python3
"""Redis Manager - Redis Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""Redis 管理器 - 全局统一使用"""
import json
from pathlib import Path
from typing import Any, Dict, Optional

import redis
import yaml


class RedisManager:
    """Redis 全局管理器"""

    _instance = None
    _client = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        config_file = Path(__file__).parent.parent / "config/redis.yaml"
        if config_file.exists():
            with open(config_file) as f:
                self._config = unified_config.get("redis_manager", {}).get("redis", {})
        else:
            self._config = {"enabled": False}

        if self._config.get("enabled", False):
            try:
                self._client = redis.Redis(
                    host=self._config.get("host", "localhost"),
                    port=self._config.get("port", 6379),
                    db=self._config.get("db", 0),
                    password=self._config.get("password") or None,
                    decode_responses=True,
                )
                self._client.ping()
                print("✅ Redis 已连接")
            except Exception as e:
                print(f"⚠️ Redis 连接失败: {e}")
                self._client = None
                self._config["enabled"] = False
        else:
            print("ℹ️ Redis 未启用，使用文件存储")

    @property
    def enabled(self):
        return self._config.get("enabled", False) and self._client is not None

    @property
    def client(self):
        return self._client

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        value = self._client.get(key)
        if value:
            try:
                return json.loads(value)
            except Exception as e:
                return value
        return None

    def set(self, key: str, value: Any, ttl: int = None):
        if not self.enabled:
            return
        if not isinstance(value, str):
            value = json.dumps(value)
        self._client.setex(key, ttl or self._config.get("session_ttl", 300), value)

    def delete(self, key: str):
        if not self.enabled:
            return
        self._client.delete(key)

    def exists(self, key: str) -> bool:
        if not self.enabled:
            return False
        return self._client.exists(key) > 0

    def get_session(self, session_id: str) -> Optional[Dict]:
        return self.get(f"session:{session_id}")

    def set_session(self, session_id: str, data: Dict, ttl: int = None):
        self.set(f"session:{session_id}", data, ttl)

    def delete_session(self, session_id: str):
        self.delete(f"session:{session_id}")


redis_manager = RedisManager()
