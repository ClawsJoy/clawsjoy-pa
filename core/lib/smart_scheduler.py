#!/usr/bin/env python3
"""Smart Scheduler - Smart Scheduler 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""智能调度器 - 统一入口"""

import importlib.util
from pathlib import Path


def _get_latest():
    lib_dir = Path(__file__).parent
    versions = []
    for f in lib_dir.glob("smart_scheduler_v*.py"):
        if f.name.startswith("smart_scheduler_v"):
            versions.append(f)
    if not versions:
        raise ImportError("未找到 smart_scheduler 模块")
    versions.sort(reverse=True)
    spec = importlib.util.spec_from_file_location("scheduler_module", versions[0])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_module = _get_latest()
smart_scheduler = _module.smart_scheduler
SmartScheduler = _module.SmartScheduler

__all__ = ["smart_scheduler", "SmartScheduler"]
