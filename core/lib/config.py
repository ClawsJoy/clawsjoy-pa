#!/usr/bin/env python3
"""统一配置管理 - 避免硬编码"""

import os
from pathlib import Path

from core.lib.unified_config import unified_config


class ServiceConfig:
    """服务配置"""

    # LLM 服务配置
    LLM_HOST = unified_config.get("llm.host", "localhost")
    LLM_PORT = unified_config.get("llm.port", 5012)
    LLM_URL = f"http://{LLM_HOST}:{LLM_PORT}"

    # Gateway 配置
    GATEWAY_HOST = unified_config.get("services.gateway.host", "0.0.0.0")
    GATEWAY_PORT = unified_config.get("services.gateway.port", 5002)

    # 超时配置
    DEFAULT_TIMEOUT = unified_config.get("timeouts.default", 30)
    LONG_TIMEOUT = unified_config.get("timeouts.long", 120)
    LLM_TIMEOUT = unified_config.get("timeouts.llm", 60)

    # 缓存配置
    CACHE_TTL = unified_config.get("cache.ttl", 1800)
    CACHE_MAX_SIZE = unified_config.get("cache.max_size", 500)

    # 限流配置
    RATE_LIMIT = unified_config.get("rate_limit.per_minute", 60)
    RATE_WINDOW = unified_config.get("rate_limit.window", 60)


# 全局配置实例
config = ServiceConfig()
