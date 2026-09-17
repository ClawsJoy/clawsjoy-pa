#!/usr/bin/env python3
"""Vector Memory Config - Vector Memory Config 模块

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

"""向量记忆配置驱动模块"""

from pathlib import Path

from core.lib.unified_config import unified_config


class VectorMemoryConfig:
    """向量记忆配置管理器"""

    def __init__(self):
        self._config = unified_config.get("vector", {})
        self._hot_reload = unified_config.get("hot_reload", {})

    @property
    def embedding_model(self) -> str:
        """embedding 模型"""
        return self._config.get("embedding_model", get_embedding_model())

    @property
    def collection_name(self) -> str:
        """集合名称"""
        return self._config.get("collection_name", "memory_vectors")

    @property
    def chunk_size(self) -> int:
        """分块大小"""
        return self._config.get("chunk_size", 512)

    @property
    def top_k(self) -> int:
        """检索数量"""
        return self._config.get("top_k", 5)

    @property
    def similarity_threshold(self) -> float:
        """相似度阈值"""
        return self._config.get("similarity_threshold", 0.3)

    @property
    def provider(self) -> str:
        """向量提供商"""
        return self._config.get("provider", "ollama")

    @property
    def auto_index(self) -> bool:
        """自动索引"""
        return self._hot_reload.get("vectorization", {}).get("auto_index", True)

    @property
    def tenant_isolated(self) -> bool:
        """租户隔离"""
        return self._hot_reload.get("tenants", {}).get("isolated_vectors", True)

    def get_embedding_function(self):
        """获取 embedding 函数"""
        if self.provider == "ollama":
            from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

            llm_config = unified_config.get("llm", {})
            url = llm_config.get("endpoint", get_llm_endpoint())
            return OllamaEmbeddingFunction(url=url, model_name=self.embedding_model)
        else:
            from chromadb.utils.embedding_functions import (
                SentenceTransformerEmbeddingFunction,
            )

            return SentenceTransformerEmbeddingFunction(model_name=self.embedding_model)

    def get_stats(self) -> dict:
        """获取配置统计"""
        return {
            "embedding_model": self.embedding_model,
            "collection_name": self.collection_name,
            "top_k": self.top_k,
            "similarity_threshold": self.similarity_threshold,
            "provider": self.provider,
            "auto_index": self.auto_index,
            "tenant_isolated": self.tenant_isolated,
        }


vector_config = VectorMemoryConfig()
