#!/usr/bin/env python3
"""Route Manager - Route Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""路由管理器 - 配置驱动 (YAML)"""
from pathlib import Path

import yaml

from core.lib.unified_config import unified_config


class RouteManager:
    _instance = None
    _routes = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        config_file = Path("config/routes/routes.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                data = unified_config.get("routes", {})
                self._routes = data.get("routes", [])
        else:
            self._routes = []

    def get_enabled_routes(self):
        return [r for r in self._routes if r.get("enabled", True)]

    def is_enabled(self, path, method):
        for r in self._routes:
            if r["path"] == path and r["method"] == method:
                return r.get("enabled", True)
        return True


route_manager = RouteManager()
