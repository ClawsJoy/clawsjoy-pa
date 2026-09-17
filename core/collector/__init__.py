#!/usr/bin/env python3
"""Init - Init 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

# 创建全局实例
from .manager import CollectorManager, collector_manager
from .safety import SafetyChecker

__all__ = ["CollectorManager", "SafetyChecker", "collector_manager"]
