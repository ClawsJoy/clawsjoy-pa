#!/usr/bin/env python3
"""Version Manager V1 0 01 20260517 - Version Manager V1 0 01 20260517 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""版本管理器 v1.0.01 - 配置驱动的版本控制"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class VersionManager:
    """版本管理器 - 统一管理所有模块版本"""

    VERSION = "1.0.01"
    RELEASE_DATE = "2026-05-17"

    def __init__(self, root_path: Optional[Path] = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent
        self.version_dir = self.root / "config" / "version"
        self.current_version_dir = self.version_dir / "current"

        # 确保目录存在
        self.version_dir.mkdir(parents=True, exist_ok=True)

        # 如果没有 current 软链接，使用最新版本
        if not self.current_version_dir.exists():
            self._init_current_version()

    def _init_current_version(self):
        """初始化当前版本指向"""
        versions = self.list_versions()
        if versions:
            latest = sorted(versions)[-1]
            target = self.version_dir / latest
            if target.exists():
                if self.current_version_dir.exists():
                    self.current_version_dir.unlink()
                self.current_version_dir.symlink_to(target, target_is_directory=True)
                print(f"📌 当前版本指向: {latest}")

    def list_versions(self) -> list:
        """列出所有版本"""
        versions = []
        for item in self.version_dir.iterdir():
            if item.is_dir() and item.name.startswith("v") and item.name != "current":
                versions.append(item.name)
        return sorted(versions)

    def get_config(self, config_name: str, module: str = "monitoring") -> Dict:
        """获取配置（支持版本化）"""
        config_file = self.current_version_dir / f"{config_name}.yaml"

        if not config_file.exists():
            config_file = self.version_dir / "default" / f"{config_name}.yaml"

        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                if config_file.suffix == ".yaml":
                    return unified_config.get("version_manager_v1_0_01_20260517", {})
                elif config_file.suffix == ".json":
                    return json.load(f)

        return {}

    def get_status(self) -> Dict:
        """获取版本状态"""
        return {
            "system_version": self.VERSION,
            "release_date": self.RELEASE_DATE,
            "current_config": (
                str(self.current_version_dir)
                if self.current_version_dir.exists()
                else None
            ),
            "available_versions": self.list_versions(),
        }


version_manager = VersionManager()
