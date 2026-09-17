#!/usr/bin/env python3
"""Version Registry V1.0.06 20260524 - Version Registry V1.0.06 20260524 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""版本注册中心 v1.0.06 - 集成智能能力模块"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class VersionRegistry:
    VERSION = "1.0.06"

    def __init__(self, root_path: Optional[Path] = None):
        self.root = root_path if root_path else Path(__file__).parent.parent
        self.json_file = self.root / "config" / "version_registry.json"
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict:
        import json

        if self.json_file.exists():
            with open(self.json_file, "r") as f:
                return json.load(f)
        return {
            "version": self.VERSION,
            "modules": {},
            "created_at": datetime.now().isoformat(),
        }

    def _save_registry(self):
        import json

        with open(self.json_file, "w") as f:
            json.dump(self.registry, f, indent=2)

    def register_module(
        self, module_name: str, module_path: str, module_type: str = "core"
    ) -> Dict:
        self.registry["modules"][module_name] = {
            "path": module_path,
            "type": module_type,
            "version": "v1.0.06",
            "registered_at": datetime.now().isoformat(),
            "status": "active",
        }
        self._save_registry()
        return self.registry["modules"][module_name]


version_registry = VersionRegistry()

# 注册智能能力模块
modules = [
    ("proactive_service", "core/lib/proactive_service.py", "intelligence"),
    ("smart_active_service", "core/lib/smart_active_service.py", "intelligence"),
    (
        "performance_predictor",
        "core/agents/core/performance_predictor.py",
        "intelligence",
    ),
    ("adaptive_optimizer", "core/intelligence/adaptive_optimizer.py", "intelligence"),
]

for name, path, typ in modules:
    try:
        version_registry.register_module(name, path, typ)
        print(f"✅ 注册: {name}")
    except Exception as e:
        print(f"❌ 注册失败 {name}: {e}")
