#!/usr/bin/env python3
"""Config Helper - Config Helper 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from core.lib.unified_config import unified_config


def get_data_root() -> str:
    """获取数据根目录"""
    return unified_config.get("paths.data_root", "data")


def get_llm_endpoint() -> str:
    """获取 LLM 端点"""
    return unified_config.get("llm.endpoint", "http://localhost:11434")


def get_llm_model(fast: bool = False) -> str:
    """获取 LLM 模型"""
    if fast:
        return unified_config.get("llm.fast_model", "qwen2.5:3b")
    return unified_config.get("llm.default_model", "qwen2.5:7b")


def get_embedding_model() -> str:
    """获取 Embedding 模型"""
    return unified_config.get("vector.embedding_model", "nomic-embed-text")


def get_gateway_port() -> int:
    """获取网关端口"""
    return unified_config.get("services.gateway.port", 5002)


def get_timeout(name: str = "default") -> int:
    """获取超时配置"""
    return unified_config.get(f"timeouts.{name}", 30)


def get_tenant_base_path() -> str:
    """获取租户基础路径"""
    return unified_config.get("tenant.base_path", "data/tenants")


def get_vector_config() -> dict:
    """获取向量配置"""
    return unified_config.get("vector", {})
