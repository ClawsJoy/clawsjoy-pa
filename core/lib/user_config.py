#!/usr/bin/env python3
"""User Config - User Config 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config


class User_config:
    def get(self, path: str = None, default=None):
        if path is None:
            return unified_config.get("user_config", {})
        return unified_config.get(f"user_config.{path}", default)


user_config = User_config()
