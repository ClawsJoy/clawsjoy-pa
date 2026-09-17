#!/usr/bin/env python3
"""Path Manager - Path Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""路径管理器 - 统一管理项目路径"""

import os
from pathlib import Path

import yaml


class PathManager:
    """路径管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        config_file = Path("config/paths.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                self.config = unified_config.get("path_manager", {})
        else:
            self.config = {}

        # 项目根目录自动检测
        self.project_root = Path(__file__).parent.parent

    def get_root(self) -> Path:
        return self.project_root

    def get(self, key: str, default: str = None) -> str:
        """获取路径配置 - 支持点号分隔"""
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default or key
            if value is None:
                return default or key
        return str(self.project_root / value) if value else str(self.project_root / key)

    def get_path(self, name: str) -> Path:
        """获取路径对象"""
        return self.project_root / self.get(name, name)


path_manager = PathManager()
