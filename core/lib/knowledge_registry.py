#!/usr/bin/env python3
"""Knowledge Registry - Knowledge Registry 模块

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

"""知识中心 - 向量化版本"""

import hashlib
import json
import time
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from core.lib.unified_config import unified_config


class KnowledgeRegistry:
    """向量化知识中心"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._init_vector_store()

    def _init_vector_store(self):
        """初始化向量存储"""
        vector_config = unified_config.get("vector", {})
        persist_dir = vector_config.get("knowledge_path", f"{get_data_root()}/knowledge")

        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        # 使用配置的 embedding 模型
        embedding_model = vector_config.get("embedding_model", get_embedding_model())

        from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

        ollama_url = unified_config.get("llm.endpoint", get_llm_endpoint())
        self.embedding_fn = OllamaEmbeddingFunction(url=ollama_url, model_name=embedding_model)

        from chromadb.config import Settings

        self.client = chromadb.PersistentClient(path=persist_dir, settings=Settings(anonymized_telemetry=False))

        collection_name = vector_config.get("knowledge_collection", "knowledge_base")

        try:
            self.collection = self.client.get_collection(collection_name)
            print(f"   ✅ 使用已有知识库: {collection_name}")
        except Exception as e:
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
            print(f"   ✅ 创建知识库: {collection_name}")

    def add_knowledge(
        self,
        title: str,
        content: str,
        category: str = "general",
        source: str = None,
        tags: list = None,
    ):
        """添加知识条目"""
        doc_id = hashlib.md5(f"{title}:{content}".encode()).hexdigest()
        self.collection.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[
                {
                    "title": title,
                    "category": category,
                    "source": source or "manual",
                    "tags": ",".join(tags or []),
                    "created": time.time(),
                }
            ],
        )
        return True

    def search(self, query: str, category: str = None, n: int = 5):
        """语义搜索知识"""
        where = {"category": category} if category else None
        results = self.collection.query(query_texts=[query], n_results=n, where=where)

        knowledge = []
        if results.get("documents") and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results.get("distances") else 0
                similarity = 1 / (1 + distance)
                knowledge.append(
                    {
                        "content": doc,
                        "title": (results["metadatas"][0][i].get("title") if results.get("metadatas") else None),
                        "category": (results["metadatas"][0][i].get("category") if results.get("metadatas") else None),
                        "similarity": similarity,
                    }
                )
        return knowledge

    def get_by_category(self, category: str):
        """按分类获取知识"""
        results = self.collection.get(where={"category": category})
        if results.get("documents"):
            return results["documents"]
        return []

    def get_stats(self):
        """获取统计信息"""
        return {
            "total_knowledge": self.collection.count(),
            "collection": self.collection.name,
        }

    def load_from_json(self, json_path: str):
        """从 JSON 文件批量导入知识 - 支持多种格式自动检测"""
        import json
        from pathlib import Path

        if not Path(json_path).exists():
            return 0

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0

        # 格式1: 标准格式 [{title, content, category}]
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    title = item.get("title", item.get("name", ""))
                    content = item.get("content", item.get("description", ""))
                    category = item.get("category", "general")
                    tags = item.get("tags", [])
                    if title and content:
                        self.add_knowledge(title, content, category, source=str(json_path), tags=tags)
                        count += 1

        # 格式2: 字典包含 knowledge_base 或 documents 数组
        elif isinstance(data, dict):
            # 检测常见的知识容器键名
            container_keys = [
                "knowledge_base",
                "documents",
                "knowledge",
                "items",
                "entries",
            ]
            items_to_process = []

            for key in container_keys:
                if key in data and isinstance(data[key], list):
                    items_to_process = data[key]
                    break

            if items_to_process:
                for item in items_to_process:
                    if isinstance(item, dict):
                        title = item.get("title", item.get("name", item.get("question", "")))
                        content = item.get("content", item.get("description", item.get("answer", "")))
                        category = item.get("category", item.get("role", "general"))
                        tags = item.get("tags", [])
                        if title and content:
                            self.add_knowledge(
                                title,
                                content,
                                category,
                                source=str(json_path),
                                tags=tags,
                            )
                            count += 1
            else:
                # 格式3: 嵌套结构如 learned_patterns
                for key, value in data.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            if isinstance(sub_value, list):
                                for item in sub_value:
                                    if isinstance(item, dict):
                                        title = str(item.get("title", item.get("analysis", sub_key)))
                                        content = item.get("content", item.get("solution", str(item)))
                                        content = content[:500] if isinstance(content, str) else str(content)[:500]
                                        category = key
                                        if title and content:
                                            self.add_knowledge(
                                                str(title),
                                                str(content),
                                                category,
                                                source=str(json_path),
                                            )
                                            count += 1
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                title = item.get("title", item.get("name", key))
                                content = item.get("content", item.get("description", ""))
                                if title and content:
                                    self.add_knowledge(
                                        str(title),
                                        str(content),
                                        "general",
                                        source=str(json_path),
                                    )
                                    count += 1

        print(f"   📚 从 {Path(json_path).name} 导入 {count} 条知识")
        return count


# 全局实例
knowledge_registry = KnowledgeRegistry()
