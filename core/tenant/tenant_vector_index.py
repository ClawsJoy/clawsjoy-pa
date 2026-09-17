#!/usr/bin/env python3
"""Tenant Vector Index - Tenant Vector Index 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""租户向量索引器"""

import hashlib
from pathlib import Path
from typing import Dict, List

from core.lib.vector_knowledge_center import vector_knowledge_center

from core.lib.unified_config import unified_config


class TenantVectorIndex:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        vector_config = unified_config.get("vector", {})
        base_path = vector_config.get("tenant_vector_path", "data/tenant_vectors")
        self.persist_dir = Path(base_path) / tenant_id
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        embedding_model = vector_config.get("embedding_model", "nomic-embed-text")
        from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

        ollama_url = unified_config.get("llm.endpoint", "http://localhost:11434")
        self.embedding_fn = OllamaEmbeddingFunction(
            url=ollama_url, model_name=embedding_model
        )

        self.client = vector_knowledge_center.client
        self.skill_collection = self.client.get_or_create_collection(
            name="tenant_skills",
            embedding_function=self.embedding_fn,
            metadata={"tenant_id": tenant_id, "type": "skills"},
        )   
    
    def index_skill(
        self, skill_id: str, name: str, description: str, category: str = "general"
    ):
        doc_id = hashlib.md5(f"{self.tenant_id}:skill:{skill_id}".encode()).hexdigest()
        self.skill_collection.upsert(
            ids=[doc_id],
            documents=[f"{name}: {description}"],
            metadatas=[
                {
                    "skill_id": skill_id,
                    "name": name,
                    "category": category,
                    "tenant_id": self.tenant_id,
                }
            ],
        )
        return True

    def search_skill(self, query: str, n: int = 5) -> List[Dict]:
        results = self.skill_collection.query(query_texts=[query], n_results=n)
        items = []
        if results.get("documents") and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results.get("distances") else 0
                similarity = 1 / (1 + distance)
                items.append(
                    {
                        "skill_id": results["metadatas"][0][i].get("skill_id"),
                        "name": results["metadatas"][0][i].get("name"),
                        "similarity": similarity,
                    }
                )
        return items

    def get_stats(self) -> Dict:
        return {"skills_indexed": self.skill_collection.count()}


class TenantIndexManager:
    def __init__(self):
        self._indexes = {}

    def get_index(self, tenant_id: str) -> TenantVectorIndex:
        if tenant_id not in self._indexes:
            self._indexes[tenant_id] = TenantVectorIndex(tenant_id)
        return self._indexes[tenant_id]


tenant_index_manager = TenantIndexManager()
