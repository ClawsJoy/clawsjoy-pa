#!/usr/bin/env python3
"""Config Loader - Config Loader 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import os
from pathlib import Path

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config


class ConfigLoader:
    """配置加载器 - 从环境变量和默认值加载"""

    @staticmethod
    def get_port(service: str = "gateway") -> int:
        ports = {
            "gateway": int(os.environ.get("GATEWAY_PORT", 5002)),
            "file_service": int(os.environ.get("FILE_SERVICE_PORT", 5003)),
            "multi_agent": int(os.environ.get("MULTI_AGENT_PORT", 5006)),
        }
        return ports.get(service, 5002)

    @staticmethod
    def get_host() -> str:
        return os.environ.get("SERVICE_HOST", "0.0.0.0")

    @staticmethod
    def get_model() -> str:
        return os.environ.get("LLM_MODEL", unified_config.get("llm.default_model", get_llm_model()))

    @staticmethod
    def get_fast_model() -> str:
        return os.environ.get(
            "LLM_FAST_MODEL",
            unified_config.get("llm.fast_model", get_llm_model(fast=True)),
        )


# 导出实例
config_loader = ConfigLoader()

# 兼容旧代码：导出 config 别名（被 config_driver.py 使用）
config = config_loader

# 导出函数（兼容旧代码）
__all__ = [
    "config_loader",
    "config",
    "get_data_root",
    "get_llm_endpoint",
    "get_llm_model",
    "get_embedding_model",
    "get_gateway_port",
    "get_timeout",
]
