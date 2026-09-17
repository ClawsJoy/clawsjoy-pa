#!/usr/bin/env python3
"""Version Registry V1.0.04 20260523 - Version Registry V1.0.04 20260523 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""版本注册中心 v1.0.04 - 配置驱动改造版"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class VersionRegistry:
    """版本注册中心 v1.0.04 - 配置驱动改造"""

    VERSION = "1.0.04"

    def __init__(self, root_path: Optional[Path] = None):
        self.root = Path(root_path) if root_path else Path(__file__).parent.parent
        self.json_file = self.root / "config" / "version_registry.json"
        self.yaml_file = self.root / "config" / "version_registry.yaml"
        self.system_version_file = self.root / "VERSION"
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict:
        if self.json_file.exists():
            with open(self.json_file, "r") as f:
                return json.load(f)
        return {
            "version": self.VERSION,
            "system_version": self._get_system_version(),
            "modules": {},
            "created_at": datetime.now().isoformat(),
            "last_updated": None,
            "format": "json",
        }

    def _save_registry(self):
        self.registry["last_updated"] = datetime.now().isoformat()
        self.registry["system_version"] = self._get_system_version()
        with open(self.json_file, "w") as f:
            json.dump(self.registry, f, indent=2, ensure_ascii=False)
        self._export_yaml()

    def _export_yaml(self):
        if not YAML_AVAILABLE:
            return
        try:
            with open(self.yaml_file, "w") as f:
                yaml.dump(self.registry, f, default_flow_style=False, allow_unicode=True)
        except Exception:
            pass

    def _get_system_version(self) -> str:
        if self.system_version_file.exists():
            return self.system_version_file.read_text().strip()
        return "5.0.0"

    def register_module(self, module_name: str, module_path: str, module_type: str = "core") -> Dict:
        """注册模块"""
        version = f"v1.0.04_20260523"
        self.registry["modules"][module_name] = {
            "path": module_path,
            "type": module_type,
            "version": version,
            "registered_at": datetime.now().isoformat(),
            "status": "active",
        }
        self._save_registry()
        return self.registry["modules"][module_name]

    def get_version(self, module_name: str) -> Optional[str]:
        if module_name in self.registry["modules"]:
            return self.registry["modules"][module_name]["version"]
        return None


# 自动注册配置驱动改造的模块
version_registry = VersionRegistry()

# 注册今天修改的核心模块
version_registry.register_module("personal_butler_v2", "core/agents/personal_butler_v2.py", "core")
version_registry.register_module("smart_adapter", "lib/smart_adapter.py", "core")
version_registry.register_module("unified_config", "core/lib/unified_config.py", "core")

print(f"[版本注册中心] v{version_registry.VERSION} 已加载，已注册配置驱动模块")
