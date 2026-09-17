#!/usr/bin/env python3
"""Closed Loop Config - Closed Loop Config 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config


class ClosedLoopConfig:
    """配置代理 - 从 unified_config 读取"""

    def get(self, path: str = None, default=None):
        if path is None:
            return unified_config.get("closed_loop", {})
        return unified_config.get(f"closed_loop.{path}", default)


closed_loop_config = ClosedLoopConfig()
