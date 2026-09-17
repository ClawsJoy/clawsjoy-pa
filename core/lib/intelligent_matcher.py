#!/usr/bin/env python3
"""Intelligent Matcher - Intelligent Matcher 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from core.lib.unified_config import unified_config
from core.tenant.tenant_vector_index import tenant_index_manager


class IntelligentMatcher:
    """统一智能匹配器 - 根据用户意图匹配最佳资源"""

    def __init__(self, tenant_id: str = "default"):
        self.tenant_id = tenant_id
        self.index = tenant_index_manager.get_index(tenant_id)
        self.config = unified_config.get("intelligent", {})
        self.top_k = self.config.get("top_k", 5)
        self.min_similarity = self.config.get("min_similarity", 0.3)

    def match_skill(self, query: str, n: int = None):
        """匹配技能"""
        n = n or self.top_k
        results = self.index.search_skill(query, n)
        return [r for r in results if r.get("similarity", 0) >= self.min_similarity]

    def match_api(self, query: str, n: int = None):
        """匹配 API"""
        n = n or self.top_k
        results = self.index.search_route(query, n)
        return [r for r in results if r.get("similarity", 0) >= self.min_similarity]

    def match_agent(self, query: str, n: int = None):
        """匹配 Agent"""
        n = n or self.top_k
        results = self.index.search_agent(query, n)
        return [r for r in results if r.get("similarity", 0) >= self.min_similarity]

    def match_all(self, query: str, n: int = None):
        """匹配所有资源类型"""
        n = n or self.top_k
        return {
            "skills": self.match_skill(query, n),
            "apis": self.match_api(query, n),
            "agents": self.match_agent(query, n),
        }

    def route_intent(self, query: str) -> dict:
        """智能路由 - 根据意图决定调用什么"""
        matches = self.match_all(query, 3)

        # 按相似度排序，取最高分
        best_skill = matches["skills"][0] if matches["skills"] else None
        best_api = matches["apis"][0] if matches["apis"] else None
        best_agent = matches["agents"][0] if matches["agents"] else None

        scores = []
        if best_skill:
            scores.append(("skill", best_skill["name"], best_skill["similarity"]))
        if best_api:
            scores.append(("api", best_api["path"], best_api["similarity"]))
        if best_agent:
            scores.append(("agent", best_agent["name"], best_agent["similarity"]))

        # 返回最佳匹配
        if scores:
            scores.sort(key=lambda x: x[2], reverse=True)
            return {
                "type": scores[0][0],
                "name": scores[0][1],
                "similarity": scores[0][2],
                "all_matches": matches,
            }

        return {
            "type": "unknown",
            "name": None,
            "similarity": 0,
            "all_matches": matches,
        }


intelligent_matcher = IntelligentMatcher()
