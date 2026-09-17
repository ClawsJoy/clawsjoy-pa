"""增强向量检索 - 混合检索 + 重排序"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from engine.lib.logger import engine_logger


@dataclass
class SearchResult:
    content: str
    score: float
    source: str
    metadata: Dict


class EnhancedVectorSearch:
    """增强向量检索 - 混合检索 + 重排序"""

    def __init__(self):
        self.vector_center = None
        self._init_vector_center()
        engine_logger.get().info("🔍 增强向量检索已初始化")

    def _init_vector_center(self):
        try:
            from core.lib.vector_knowledge_center import vector_knowledge_center

            self.vector_center = vector_knowledge_center
        except Exception as e:
            pass

    def hybrid_search(
        self, query: str, top_k: int = 10, keyword_weight: float = 0.3
    ) -> List[SearchResult]:
        """混合检索 - 向量 + 关键词"""
        results = []

        # 1. 向量检索
        vector_results = []
        if self.vector_center:
            try:
                vector_results = self.vector_center.search(query, n=top_k)
            except Exception as e:
                pass

        # 2. 关键词检索
        keyword_results = self._keyword_search(query, top_k)

        # 3. 融合排序
        combined = self._fusion_results(vector_results, keyword_results, keyword_weight)

        return combined[:top_k]

    def _keyword_search(self, query: str, top_k: int) -> List[SearchResult]:
        """关键词检索"""
        results = []
        query_lower = query.lower()

        # 从技能库中检索
        try:
            from engine.skill_matrix.core import skill_matrix_engine

            for name, info in skill_matrix_engine.skills.items():
                score = 0
                if query_lower in name.lower():
                    score += 10
                if query_lower in info.get("category", "").lower():
                    score += 5
                for kw in info.get("keywords", []):
                    if query_lower in kw.lower():
                        score += 3
                if score > 0:
                    results.append(
                        SearchResult(
                            content=name,
                            score=score / 10,
                            source="keyword",
                            metadata=info,
                        )
                    )
        except Exception as e:
            pass

        return sorted(results, key=lambda x: -x.score)[:top_k]

    def _fusion_results(
        self, vector_results: List, keyword_results: List, keyword_weight: float
    ) -> List[SearchResult]:
        """融合向量和关键词结果"""
        combined = {}

        # 向量结果
        for vr in vector_results:
            content = vr.get("content", "")
            score = vr.get("score", 0)
            if content:
                combined[content] = {
                    "score": score * (1 - keyword_weight),
                    "source": "vector",
                    "metadata": vr.get("metadata", {}),
                }

        # 关键词结果
        for kr in keyword_results:
            content = kr.content
            score = kr.score * keyword_weight
            if content in combined:
                combined[content]["score"] += score
                combined[content]["source"] = "hybrid"
            else:
                combined[content] = {
                    "score": score,
                    "source": "keyword",
                    "metadata": kr.metadata,
                }

        # 排序
        sorted_results = sorted(combined.items(), key=lambda x: -x[1]["score"])
        return [
            SearchResult(
                content=content,
                score=data["score"],
                source=data["source"],
                metadata=data["metadata"],
            )
            for content, data in sorted_results
        ]

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """简化的搜索接口"""
        return self.hybrid_search(query, top_k)

    def get_stats(self) -> Dict:
        return {"status": "active", "hybrid_search": True}


enhanced_vector_search = EnhancedVectorSearch()
