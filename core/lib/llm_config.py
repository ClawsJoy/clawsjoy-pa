#!/usr/bin/env python3
"""Llm Config - Llm Config 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config


class Llm_config:
    def get(self, path: str = None, default=None):
        if path is None:
            return unified_config.get("llm_config", {})
        return unified_config.get(f"llm_config.{path}", default)


llm_config = Llm_config()
