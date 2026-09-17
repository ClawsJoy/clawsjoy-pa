#!/usr/bin/env python3
"""Clawsjoy Config - Clawsjoy Config 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config


class Clawsjoy_config:
    def get(self, path: str = None, default=None):
        if path is None:
            return unified_config.get("clawsjoy_config", {})
        return unified_config.get(f"clawsjoy_config.{path}", default)


clawsjoy_config = Clawsjoy_config()
