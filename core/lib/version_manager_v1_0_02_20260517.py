#!/usr/bin/env python3
"""Version Manager V1 0 02 20260517 - Version Manager V1 0 02 20260517 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""版本管理器 v1.0.02 - 配置驱动版"""

from pathlib import Path
from typing import Dict, Optional

from core.lib.config_driver_v1_0_00_20260517 import config_driver
from core.lib.unified_config import unified_config


class VersionManager:
    """版本管理器 - 配置驱动版"""

    VERSION = "1.0.02"

    def __init__(self):
        self.root = unified_config.ROOT
        self.version_dir = self.root / "config" / "version"
        self.enabled = config_driver.get("optimization.enable_versioning", True)

    def get_current_version(self) -> str:
        if not self.enabled:
            return "versioning_disabled"

        current_link = self.version_dir / "current"
        if current_link.exists():
            return (
                current_link.readlink().name
                if hasattr(current_link, "readlink")
                else str(current_link)
            )
        return "unknown"

    def get_status(self) -> Dict:
        return {
            "version": self.VERSION,
            "enabled": self.enabled,
            "current": self.get_current_version(),
            "config_driver": config_driver.get_status(),
        }


version_manager = VersionManager()
