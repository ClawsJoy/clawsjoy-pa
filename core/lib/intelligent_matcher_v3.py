#!/usr/bin/env python3
"""Intelligent Matcher V3 - Intelligent Matcher V3 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from core.tenant.tenant_vector_index import tenant_index_manager


class IntelligentMatcherV3:
    def __init__(self, tenant_id: str = "default"):
        self.tenant_id = tenant_id
        self.index = tenant_index_manager.get_index(tenant_id)
        self.top_k = 5
        self.min_similarity = 0.5

    def match_skill(self, query: str, n: int = None):
        n = n or self.top_k
        results = self.index.search_skill(query, n)

        # 名称精确匹配提权
        for r in results:
            name = r.get("name", "").lower()
            if name == query.lower():
                r["similarity"] = r["similarity"] * 2.0
            elif query.lower() in name:
                r["similarity"] = r["similarity"] * 1.5

        results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return [r for r in results if r.get("similarity", 0) >= self.min_similarity]

    def route_intent(self, query: str) -> dict:
        skills = self.match_skill(query, 3)

        if skills:
            best = skills[0]
            return {
                "type": "skill",
                "name": best["name"],
                "similarity": best["similarity"],
                "is_exact": best["name"].lower() == query.lower(),
            }

        return {"type": "unknown", "name": None, "similarity": 0}


matcher = IntelligentMatcherV3()

# 测试
print("\n测试:")
for q in ["计算", "翻译", "天气", "文件"]:
    result = matcher.route_intent(q)
    print(
        f"  {q} -> {result['name']} (相似度: {result['similarity']:.3f}, 精确: {result['is_exact']})"
    )
