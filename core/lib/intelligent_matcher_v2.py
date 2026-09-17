#!/usr/bin/env python3
"""Intelligent Matcher V2 - Intelligent Matcher V2 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from core.similarity_optimizer import similarity_optimizer
from core.tenant.tenant_vector_index import tenant_index_manager


class IntelligentMatcherV2:
    """统一智能匹配器 V2"""

    def __init__(self, tenant_id: str = "default"):
        self.tenant_id = tenant_id
        self.index = tenant_index_manager.get_index(tenant_id)
        self.top_k = 5
        self.min_similarity = 0.5

    def match_skill(self, query: str, n: int = None):
        n = n or self.top_k
        results = self.index.search_skill(query, n)

        # 技能提权
        boost_keywords = {
            "计算": 1.1,
            "翻译": 1.1,
            "天气": 1.1,
            "文件": 1.1,
            "读取": 1.1,
            "列表": 1.1,
        }

        results = similarity_optimizer.rerank(results, query, boost_keywords)
        results = similarity_optimizer.filter_by_threshold(results, self.min_similarity)
        return results

    def match_api(self, query: str, n: int = None):
        n = n or self.top_k
        results = self.index.search_route(query, n)
        results = similarity_optimizer.filter_by_threshold(results, self.min_similarity)
        return results

    def match_agent(self, query: str, n: int = None):
        n = n or self.top_k
        results = self.index.search_agent(query, n)
        results = similarity_optimizer.filter_by_threshold(results, self.min_similarity)
        return results

    def match_all(self, query: str, n: int = None):
        n = n or self.top_k
        return {
            "skills": self.match_skill(query, n),
            "apis": self.match_api(query, n),
            "agents": self.match_agent(query, n),
        }

    def route_intent(self, query: str) -> dict:
        matches = self.match_all(query, 5)

        all_results = []
        for skill in matches["skills"]:
            all_results.append(("skill", skill["name"], skill["similarity"], skill))
        for api in matches["apis"]:
            all_results.append(("api", api["path"], api["similarity"], api))
        for agent in matches["agents"]:
            all_results.append(("agent", agent["name"], agent["similarity"], agent))

        if all_results:
            all_results.sort(key=lambda x: x[2], reverse=True)
            best = all_results[0]
            return {
                "type": best[0],
                "name": best[1],
                "similarity": best[2],
                "detail": best[3],
            }

        return {"type": "unknown", "name": None, "similarity": 0}


intelligent_matcher_v2 = IntelligentMatcherV2()
