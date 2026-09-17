#!/usr/bin/env python3
"""Driver Manager - Driver Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""智能驱动管理器 - 统一管理所有配置驱动"""

import importlib
import threading
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class DriverManager:
    """智能驱动管理器单例"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.drivers = {}
        self.driver_path = Path("config/drivers")
        self.driver_path.mkdir(parents=True, exist_ok=True)
        self._load_all_drivers()

    def _load_all_drivers(self):
        """加载所有驱动配置"""
        for yaml_file in self.driver_path.glob("*.yaml"):
            try:
                with open(yaml_file, "r") as f:
                    config = unified_config.get("drivers", {})
                    driver_name = config.get("driver_name", yaml_file.stem)
                    self.drivers[driver_name] = config
                    print(f"✅ 加载驱动: {driver_name}")
            except Exception as e:
                print(f"⚠️ 加载驱动失败 {yaml_file}: {e}")

    def get_driver(self, name: str) -> Optional[Dict]:
        """获取驱动配置"""
        return self.drivers.get(name)

    def reload(self):
        """热重载所有驱动"""
        self.drivers.clear()
        self._load_all_drivers()
        print("✅ 驱动配置已热重载")


driver_manager = DriverManager()
