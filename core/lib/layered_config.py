#!/usr/bin/env python3
"""Layered Config - Layered Config 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config


class Layered_config:
    def get(self, path: str = None, default=None):
        if path is None:
            return unified_config.get("layered_config", {})
        return unified_config.get(f"layered_config.{path}", default)


layered_config = Layered_config()
