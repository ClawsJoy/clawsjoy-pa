#!/usr/bin/env python3
"""Agent Registry Config - Agent Registry Config 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config


class Agent_registry_config:
    def get(self, path: str = None, default=None):
        if path is None:
            return unified_config.get("agent_registry_config", {})
        return unified_config.get(f"agent_registry_config.{path}", default)


agent_registry_config = Agent_registry_config()
