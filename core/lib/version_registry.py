#!/usr/bin/env python3
"""Version Registry - Version Registry 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""版本注册中心 - 统一导入入口（自动使用最新版本）"""

import re
import sys
from pathlib import Path


def _get_latest_version_file():
    """获取最新的版本注册中心文件路径"""
    lib_dir = Path(__file__).parent
    pattern = r"version_registry_v(\d+\.\d+\.\d+)_(\d{8})\.py"

    versions = []
    for f in lib_dir.glob("version_registry_v*.py"):
        match = re.search(pattern, f.name)
        if match:
            major, minor, patch = map(int, match.group(1).split("."))
            date = match.group(2)
            versions.append(((major, minor, patch, date), f))

    if not versions:
        raise ImportError("未找到版本注册中心模块")

    versions.sort(key=lambda x: x[0])
    latest = versions[-1][1]
    return latest


# 获取最新版本文件
_version_file = _get_latest_version_file()
_version_name = _version_file.stem

# 动态加载
import importlib.util

spec = importlib.util.spec_from_file_location(_version_name, _version_file)
_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_module)

# 导出主要对象
version_registry = _module.version_registry
VersionRegistry = _module.VersionRegistry

# 打印加载信息（可选，生产环境可注释）
print(f"[版本注册中心] 已加载: {_version_name}")

__all__ = ["version_registry", "VersionRegistry"]
