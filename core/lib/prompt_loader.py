#!/usr/bin/env python3
"""Prompt Loader - Prompt Loader 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""提示词加载器 - 从配置文件加载，消除硬编码"""

from pathlib import Path
from typing import Any, Dict

import yaml


class PromptLoader:
    """提示词加载器"""

    _instance = None
    _prompts = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        config_file = Path(__file__).parent.parent / "config/prompts.yaml"
        if config_file.exists():
            with open(config_file, "r") as f:
                self._prompts = unified_config.get("prompt_loader", {})
        else:
            self._prompts = self._get_default()

    def _get_default(self):
        return {"system": {"default": "你是一个智能助手。"}, "tasks": {}, "skills": {}}

    def get(self, path: str, **kwargs) -> str:
        """获取提示词，支持变量替换"""
        parts = path.split(".")
        value = self._prompts
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part, {})
            else:
                break

        if isinstance(value, str):
            return value.format(**kwargs) if kwargs else value
        return str(value) if value else ""


prompt_loader = PromptLoader()
