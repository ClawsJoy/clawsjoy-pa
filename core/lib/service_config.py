#!/usr/bin/env python3
"""Service Config - Service Config 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config


class Service_config:
    def get(self, path: str = None, default=None):
        if path is None:
            return unified_config.get("service_config", {})
        return unified_config.get(f"service_config.{path}", default)


service_config = Service_config()
