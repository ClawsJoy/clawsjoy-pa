#!/usr/bin/env python3
"""Skill Search - Skill Search 模块

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
from core.lib.unified_config import unified_config

"""技能向量搜索 - 使用专用索引"""


class SkillSearch:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        from core.lib.vector_knowledge_center import vector_knowledge_center

        self.client = vector_knowledge_center.client
        try:
            self.collection = self.client.get_collection("skill_vectors")
        except Exception as e:
            self.collection = None

    def search(self, query: str, n: int = 10):
        if not self.collection:
            return []
        results = self.collection.query(query_texts=[query], n_results=n)
        skills = []
        for i, meta in enumerate(results["metadatas"][0]):
            skills.append(
                {
                    "name": meta.get("skill_name", "unknown"),
                    "category": meta.get("category", "general"),
                    "description": meta.get("description", ""),
                    "score": (1 - results["distances"][0][i] if results["distances"] else 0),
                }
            )
        return skills


skill_search = SkillSearch()
