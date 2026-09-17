#!/usr/bin/env python3
"""Unified Config - Unified Config 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class UnifiedConfig:
    """统一配置管理器 - 单例模式"""

    _instance = None
    _config: Dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _find_file(self, candidates: list) -> Optional[Path]:
        """在多个候选路径中查找文件"""
        for candidate in candidates:
            path = Path(candidate)
            if path.exists():
                return path
        return None

    def _load_yaml(self, path: Path, key: str = None):
        """加载 YAML 文件"""
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
                if key:
                    self._config[key] = data
                else:
                    self._config.update(data)
            print(f"[CONFIG] 加载: {path}")
            return True
        except Exception as e:
            print(f"[CONFIG] 加载失败 {path}: {e}")
            return False

    def _load(self):
        """加载所有配置 - 支持多路径查找"""
        print("[CONFIG] 初始化统一配置管理器")

        # 主配置文件
        main_paths = [
            "config/system/system_unified.yaml",
            "config/system.yaml",
            "config/config.yaml",
        ]
        main_path = self._find_file(main_paths)
        if main_path:
            self._load_yaml(main_path)

        # 路由配置
        routes_paths = ["config/routes/routes.yaml", "config/routes.yaml"]
        routes_path = self._find_file(routes_paths)
        if routes_path:
            self._load_yaml(routes_path, "routes")

        # Agent Soul 配置
        soul_paths = ["config/agents_soul/agents_soul.yaml", "config/agents_soul.yaml"]
        soul_path = self._find_file(soul_paths)
        if soul_path:
            self._load_yaml(soul_path, "agents_soul")

        # 关键词配置 (统一关键词配置)
        keywords_paths = [
            "config/keywords.yaml",
        ]
        keywords_path = self._find_file(keywords_paths)
        if keywords_path:
            self._load_yaml(keywords_path, "keywords")

    def get(self, path: str, default=None):
        """获取配置值，支持点号路径如 'llm.model'"""
        keys = path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value if value is not None else default

    def get_port(self, service: str = "gateway") -> int:
        """获取服务端口"""
        ports = self.get("services", {})
        if isinstance(ports, dict):
            return ports.get(service, {}).get("port", 5002)
        return 5002

    @property
    def ROOT(self) -> str:
        """项目根目录"""
        return str(Path(__file__).parent.parent.parent.absolute())

    @property
    def HOST(self) -> str:
        """服务主机"""
        return self.get("services.host", "localhost")


# 全局单例
unified_config = UnifiedConfig()
