#!/usr/bin/env python3
"""Config Finder - Config Finder 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from pathlib import Path
from typing import List, Optional


def find_config(candidates: List[str]) -> Optional[Path]:
    """
    在多个候选路径中查找配置文件

    Args:
        candidates: 候选路径列表

    Returns:
        存在的第一个路径，否则 None
    """
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return path
    return None


def get_config_path(config_name: str) -> Optional[Path]:
    """
    根据配置名称获取标准路径

    标准路径优先级:
    1. config/{category}/{name}.yaml
    2. config/{name}.yaml
    """
    categories = {
        "routes": ["config/routes/routes.yaml", "config/routes.yaml"],
        "routes_unified": [
            "config/routes/routes_unified.yaml",
            "config/routes_unified.yaml",
        ],
        "routes_local": ["config/routes/routes_local.yaml", "config/routes_local.yaml"],
        "routes_sandbox": [
            "config/routes/routes_sandbox.yaml",
            "config/routes_sandbox.yaml",
        ],
        "agents_soul": [
            "config/agents_soul/agents_soul.yaml",
            "config/agents_soul.yaml",
        ],
        "system": ["config/system/system_unified.yaml", "config/system_unified.yaml"],
        "butler": ["config/butler/butler.yaml", "config/butler.yaml"],
        "scriptbook": ["config/butler/scriptbook.yaml", "config/scriptbook.yaml"],
    }

    candidates = categories.get(config_name, [config_name])
    return find_config(candidates)


# 导出常用配置路径
ROUTES_CONFIG = get_config_path("routes")
SOUL_CONFIG = get_config_path("agents_soul")
SYSTEM_CONFIG = get_config_path("system")
