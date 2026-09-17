#!/usr/bin/env python3
"""Port Manager - Port Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""统一端口管理 - 配置驱动"""

import os
from pathlib import Path

import yaml


class PortManager:
    """端口管理器单例"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        """加载端口配置"""
        self._ports = {}
        config_path = Path("config/ports.yaml")
        if config_path.exists():
            with open(config_path) as f:
                config = unified_config.get("port_manager", {})
                self._ports = config.get("ports", {})

        # 环境变量覆盖
        overrides = config.get("env_overrides", {})
        for env, name in overrides.items():
            if os.environ.get(env):
                self._ports[name] = int(os.environ[env])

    def get(self, service: str, default: int = 5000) -> int:
        """获取端口号"""
        return self._ports.get(service, default)


port_manager = PortManager()
