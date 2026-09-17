#!/usr/bin/env python3
"""Config Inherit - Config Inherit 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from pathlib import Path
from typing import Any, Dict

import yaml


class ConfigInherit:
    """配置继承 - 支持多层覆盖"""

    def __init__(self):
        self.configs: Dict[str, Dict] = {}

    def load_with_inherit(self, config_path: Path, inherit_from: list = None) -> Dict:
        """加载配置，支持继承"""
        result = {}

        # 1. 加载继承的配置
        if inherit_from:
            for parent in inherit_from:
                parent_path = Path(parent)
                if parent_path.exists():
                    with open(parent_path, "r") as f:
                        parent_config = yaml.safe_load(f)
                        self._deep_merge(result, parent_config)

        # 2. 加载当前配置
        if config_path.exists():
            with open(config_path, "r") as f:
                current_config = yaml.safe_load(f)
                self._deep_merge(result, current_config)

        return result

    def _deep_merge(self, base: Dict, override: Dict):
        """深度合并字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value


config_inherit = ConfigInherit()
