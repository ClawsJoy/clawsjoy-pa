#!/usr/bin/env python3
"""Unified Vector - Unified Vector 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from core.lib.knowledge_registry import knowledge_registry
from core.lib.memory import memory
from core.lib.route_vectorizer import route_vectorizer
from core.lib.unified_config import unified_config
from core.tenant.tenant_vector_index import tenant_index_manager


class UnifiedVector:
    """统一向量管理器 - 所有向量操作的统一入口"""

    def __init__(self):
        self.config = unified_config.get("vectorization", {})
        self.enabled = self.config.get("enabled", True)

    def index_skill(
        self,
        tenant_id: str,
        skill_id: str,
        name: str,
        description: str,
        category: str = "general",
    ):
        """索引技能"""
        if not self.enabled:
            return None
        if not self.config.get("types", {}).get("skills", {}).get("enabled", True):
            return None
        return tenant_index_manager.index_skill(
            tenant_id, skill_id, name, description, category
        )

    def search_skills(self, tenant_id: str, query: str, n: int = None):
        """搜索技能"""
        if not self.enabled:
            return []
        n = n or self.config.get("recommendation", {}).get("default_top_k", 5)
        min_sim = self.config.get("recommendation", {}).get("min_similarity", 0.3)

        results = tenant_index_manager.search_skills(tenant_id, query, n)
        # 过滤低相似度结果
        return [r for r in results if r.get("similarity", 0) >= min_sim]

    def match_route(self, tenant_id: str, query: str, n: int = None):
        """意图路由匹配"""
        if not self.enabled:
            return []
        n = n or self.config.get("recommendation", {}).get("default_top_k", 3)
        return route_vectorizer.match_route(tenant_id, query, n)

    def search_knowledge(self, query: str, n: int = None):
        """搜索知识库"""
        if not self.enabled:
            return []
        n = n or self.config.get("recommendation", {}).get("default_top_k", 5)
        return knowledge_registry.search(query, n=n)

    def recall_memories(self, user_id: str, query: str, n: int = None):
        """召回记忆"""
        if not self.enabled:
            return []
        n = n or self.config.get("recommendation", {}).get("default_top_k", 5)
        return memory.recall_with_scores(query, user_id=user_id, n=n)

    def get_stats(self, tenant_id: str = "default"):
        """获取所有向量统计"""
        return {
            "enabled": self.enabled,
            "skills": tenant_index_manager.get_index(tenant_id).get_stats(),
            "routes": route_vectorizer.get_stats(tenant_id),
            "knowledge": knowledge_registry.get_stats(),
            "memories": memory.get_stats(),
        }


unified_vector = UnifiedVector()
