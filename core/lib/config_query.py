#!/usr/bin/env python3
"""Config Query - Config Query 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""配置查询模块"""

from pathlib import Path

from core.lib.constants import PROJECT_ROOT


class ConfigQuery:
    def __init__(self):
        self.config_dir = PROJECT_ROOT / "config"

    def get(self, key: str, default=None):
        # 简化实现
        return default


config_query = ConfigQuery()
# DEPRECATED: 请使用 unified_config 代替
