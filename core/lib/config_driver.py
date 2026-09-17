#!/usr/bin/env python3
"""Config Driver - Config Driver 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from typing import Dict

#!/usr/bin/env python3
"""配置驱动核心 - 向后兼容接口"""

from core.lib.config_loader import config
from core.lib.unified_config import unified_config


class ConfigDriverCompatible:
    """向后兼容的配置驱动接口"""

    @property
    def VERSION(self) -> str:
        return getattr(config, "VERSION", "1.0.0")

    def get(self, key: str, default=None):
        return (
            config.get(key, default)
            if hasattr(config, "get")
            else unified_config.get(key, default)
        )

    def get_port(self, service: str) -> int:
        if hasattr(config, "get_port"):
            return config.get_port(service)
        return unified_config.get_port(service)

    def get_path(self, name: str) -> str:
        if hasattr(config, "get_path"):
            return config.get_path(name)
        return unified_config.get(f"paths.{name}", "")

    def is_enabled(self, feature: str) -> bool:
        if hasattr(config, "is_enabled"):
            return config.is_enabled(feature)
        return unified_config.get(f"features.{feature}", False)

    def reload(self):
        if hasattr(config, "reload"):
            config.reload()
        # unified_config 没有 reload，跳过

    def get_status(self) -> Dict:
        if hasattr(config, "get_status"):
            return config.get_status()
        return {"status": "ok", "source": "unified_config"}


config_driver = ConfigDriverCompatible()


if __name__ == "__main__":
    print(f"配置驱动 v{config_driver.VERSION}")
    print(f"gateway 端口: {config_driver.get_port('gateway')}")
    print(f"智能调度启用: {config_driver.is_enabled('enable_smart_scheduling')}")
