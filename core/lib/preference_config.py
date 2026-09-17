#!/usr/bin/env python3
"""Preference Config - Preference Config 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from pathlib import Path
from typing import Dict, List, Optional

import yaml


class PreferenceConfig:
    """偏好配置管理器"""

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        """加载配置"""
        config_file = Path("config/butler/preferences.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                self._config = yaml.safe_load(f)
        else:
            self._config = {
                "extraction_patterns": [],
                "query_patterns": [],
                "storage": {"like_key": "likes"},
            }

    def get_extraction_patterns(self) -> List[Dict]:
        """获取提取模式"""
        return self._config.get("extraction_patterns", [])

    def get_query_patterns(self) -> List[Dict]:
        """获取查询模式"""
        return self._config.get("query_patterns", [])

    def get_storage_key(self, type_name: str) -> str:
        """获取存储键名"""
        return self._config.get("storage", {}).get(f"{type_name}_key", type_name)

    def reload(self):
        """重新加载配置"""
        self._load()


preference_config = PreferenceConfig()
