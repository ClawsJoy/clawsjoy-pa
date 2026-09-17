#!/usr/bin/env python3
"""Similarity Optimizer - Similarity Optimizer 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from typing import Dict, List


class SimilarityOptimizer:
    """相似度优化器 - 保持原始分数"""

    @staticmethod
    def rerank(
        results: List[Dict], query: str, boost_keywords: dict = None
    ) -> List[Dict]:
        """重排序结果，保持原始分数"""
        if not results:
            return results

        # 关键词提权 (轻量)
        if boost_keywords:
            for r in results:
                name = r.get("name", "").lower()
                boost = 1.0
                for keyword, multiplier in boost_keywords.items():
                    if keyword in name:
                        boost = max(boost, multiplier)
                r["similarity"] = r["similarity"] * boost

        # 按相似度排序
        results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return results

    @staticmethod
    def filter_by_threshold(results: List[Dict], threshold: float = 0.5) -> List[Dict]:
        """过滤低分结果"""
        return [r for r in results if r.get("similarity", 0) >= threshold]


similarity_optimizer = SimilarityOptimizer()
