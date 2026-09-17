#!/usr/bin/env python3
"""Knowledge Config - Knowledge Config 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)

"""知识中心配置驱动"""

from core.lib.unified_config import unified_config


class KnowledgeConfig:
    """知识中心配置"""

    def __init__(self):
        self._config = unified_config.get("knowledge", {})

    @property
    def enabled(self) -> bool:
        return self._config.get("enabled", True)

    @property
    def embedding_model(self) -> str:
        return self._config.get("embedding_model", get_embedding_model())

    @property
    def collection_name(self) -> str:
        return self._config.get("collection_name", "knowledge_base")

    @property
    def chunk_size(self) -> int:
        return self._config.get("chunk_size", 512)

    @property
    def top_k(self) -> int:
        return self._config.get("top_k", 5)


knowledge_config = KnowledgeConfig()
