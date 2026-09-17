#!/usr/bin/env python3
"""Route Registry - Route Registry 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from pathlib import Path

import yaml
from flask import jsonify, request

from core.lib.unified_config import unified_config


class RouteRegistry:
    """路由注册中心 - 支持多配置文件"""

    _instance = None
    _routes = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _find_config(self, candidates: list) -> Path:
        """查找配置文件"""
        for candidate in candidates:
            path = Path(candidate)
            if path.exists():
                return path
        return None

    def _load_from_file(self, file_path: Path):
        """从文件加载路由"""
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)

            routes = []
            if isinstance(data, dict):
                if "routes" in data:
                    routes = data["routes"]
                else:
                    for key, value in data.items():
                        if isinstance(value, list):
                            for item in value:
                                if "handler" in item and "path" in item:
                                    self._add_route(item)
                    return
            elif isinstance(data, list):
                routes = data
            else:
                return

            for route in routes:
                self._add_route(route)
        except Exception as e:
            print(f"   ⚠️ 加载路由文件失败 {file_path}: {e}")

    def _load(self):
        """加载所有路由配置文件"""
        self._routes = {}

        # 查找主路由配置
        candidates = [
            "config/routes/routes.yaml",
            "config/routes/routes.yaml",
        ]
        main_config = self._find_config(candidates)
        if main_config:
            self._load_from_file(main_config)

        # 查找统一路由配置
        unified_candidates = [
            "config/routes/routes_unified.yaml",
            "config/routes_unified.yaml",
        ]
        unified_config_file = self._find_config(unified_candidates)
        if unified_config_file:
            self._load_from_file(unified_config_file)

        # 查找本地路由配置
        local_candidates = [
            "config/routes/routes_local.yaml",
            "config/routes_local.yaml",
        ]
        local_config = self._find_config(local_candidates)
        if local_config:
            self._load_from_file(local_config)

        # 查找沙箱路由配置
        sandbox_candidates = [
            "config/routes/routes_sandbox.yaml",
            "config/routes_sandbox.yaml",
        ]
        sandbox_config = self._find_config(sandbox_candidates)
        if sandbox_config:
            self._load_from_file(sandbox_config)

        print(f"   📍 路由注册中心已加载 {len(self._routes)} 个路由")

    def _add_route(self, route):
        if not route.get("enabled", True):
            return

        method = route.get("method", "GET")
        path = route.get("path", "")
        handler = route.get("handler", "")

        if path and handler:
            key = f"{method}:{path}"
            if key not in self._routes:
                self._routes[key] = route

    def get_route(self, method, path):
        return self._routes.get(f"{method}:{path}")

    def get_all_enabled(self):
        return [r for r in self._routes.values() if r.get("enabled", True)]

    def reload(self):
        """热重载路由配置"""
        print("🔄 热重载路由...")
        old_count = len(self._routes)
        self._load()
        new_count = len(self._routes)
        print(f"   ✅ 路由已重载: {old_count} -> {new_count}")
        return new_count

    def register_to_app(self, app, handlers):
        registered = 0
        for route in self.get_all_enabled():
            method = route["method"].lower()
            path = route["path"]
            handler_name = route["handler"]

            if handler_name in handlers:
                app.add_url_rule(
                    path, view_func=handlers[handler_name], methods=[method.upper()]
                )
                registered += 1
            else:
                print(f"   ⚠️ 处理器未找到: {handler_name}")

        print(f"   ✅ 已注册 {registered} 个路由")
        return registered


route_registry = RouteRegistry()
