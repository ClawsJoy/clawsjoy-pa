#!/usr/bin/env python3
"""Agent Lifecycle Config - Agent Lifecycle Config 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config


class AgentLifecycleConfig:
    def get(self, path: str = None, default=None):
        if path is None:
            return unified_config.get("agent_lifecycle", {})
        return unified_config.get(f"agent_lifecycle.{path}", default)


agent_lifecycle_config = AgentLifecycleConfig()
