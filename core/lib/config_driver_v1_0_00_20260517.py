#!/usr/bin/env python3
"""Config Driver V1 0 00 20260517 - Config Driver V1 0 00 20260517 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""配置驱动核心 v1.0.00 - 统一配置管理"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from core.lib.unified_config import unified_config


class ConfigDriver:
    """配置驱动核心 - 所有配置从这里读取"""

    VERSION = "1.0.00"

    def __init__(self):
        self.root = unified_config.ROOT
        self.config_dir = self.root / "config" / "driver"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 配置缓存
        self._cache = {}

        # 加载所有配置
        self._load_all_configs()

    def _load_all_configs(self):
        """加载所有配置文件"""
        config_files = [
            ("thresholds", "thresholds.yaml"),
            ("optimization", "optimization.yaml"),
            ("monitoring", "monitoring.yaml"),
            ("resources", "resources.yaml"),
            ("tasks", "tasks.yaml"),
        ]

        for name, filename in config_files:
            self._load_config(name, filename)

    def _load_config(self, name: str, filename: str):
        """加载单个配置文件"""
        file_path = self.config_dir / filename
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                if filename.endswith(".yaml") or filename.endswith(".yml"):
                    self._cache[name] = unified_config.get(
                        "config_driver_v1_0_00_20260517", {}
                    )
                elif filename.endswith(".json"):
                    self._cache[name] = json.load(f)
        else:
            # 使用默认配置
            self._cache[name] = self._get_default_config(name)

    def _get_default_config(self, name: str) -> Dict:
        """获取默认配置"""
        defaults = {
            "thresholds": {
                "quality_min_score": 0.5,
                "max_retry_same_error": 3,
                "success_rate_warning": 50,
                "success_rate_critical": 30,
                "cpu_threshold": 80,
                "memory_threshold": 85,
                "disk_threshold": 90,
            },
            "optimization": {
                "enable_quality_scoring": True,
                "enable_error_knowledge": True,
                "enable_priority_adjust": True,
                "enable_resource_throttle": True,
                "skip_on_low_quality": True,
                "skip_on_repeated_failure": True,
                "history_window_size": 100,
            },
            "monitoring": {
                "source": "log",
                "log_path": "logs/active_runner.log",
                "success_pattern": "✅ 完成",
                "failure_pattern": "❌ 失败",
                "window_size": 100,
            },
            "resources": {
                "check_interval": 60,
                "throttle_when_high_load": True,
                "cooldown_seconds": 30,
            },
            "tasks": {
                "default_priority": 2,
                "max_concurrent": 5,
                "retry_delay": 5,
                "queue_persist": True,
            },
        }
        return defaults.get(name, {})

    @lru_cache(maxsize=128)
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔，如 'thresholds.quality_min_score'"""
        parts = key.split(".")
        value = self._cache

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def get_section(self, section: str) -> Dict:
        """获取整个配置节"""
        return self._cache.get(section, {})

    def reload(self):
        """重新加载配置"""
        self._cache.clear()
        self._load_all_configs()
        print("✅ 配置已重新加载")

    def get_status(self) -> Dict:
        """获取配置驱动状态"""
        return {
            "version": self.VERSION,
            "config_dir": str(self.config_dir),
            "loaded_sections": list(self._cache.keys()),
            "cache_size": len(self._cache),
        }


# 全局实例
config_driver = ConfigDriver()


if __name__ == "__main__":
    print(f"配置驱动 v{config_driver.VERSION}")
    print(f"状态: {config_driver.get_status()}")
    print(f"\n阈值配置:")
    print(f"  quality_min_score: {config_driver.get('thresholds.quality_min_score')}")
    print(
        f"  max_retry_same_error: {config_driver.get('thresholds.max_retry_same_error')}"
    )
    print(f"\n优化开关:")
    print(
        f"  enable_quality_scoring: {config_driver.get('optimization.enable_quality_scoring')}"
    )
    print(
        f"  enable_error_knowledge: {config_driver.get('optimization.enable_error_knowledge')}"
    )
# DEPRECATED: 请使用 unified_config 代替
