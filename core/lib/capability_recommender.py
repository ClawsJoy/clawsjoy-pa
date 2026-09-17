#!/usr/bin/env python3
"""能力推荐器 - LLM 推荐 Top 3 能力（增强版）"""

import re
import hashlib
import time
from typing import List, Dict, Any, Optional

from core.lib.llm_client import llm_client
from core.lib.unified_capability_loader import unified_capability_loader


class CapabilityRecommender:
    """LLM 驱动的能力推荐器 - 关键词+LLM双路+缓存"""

    def __init__(self, model: str = "qwen2.5:7b-instruct-q4_0-gpu"):
        self.model = model
        self.llm = llm_client
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 3600

    # ====================================================================
    #  主推荐入口
    # ====================================================================

    def recommend(self, user_input: str, types: List[str] = None,
                  n: int = 3) -> List[Dict[str, Any]]:
        """推荐 Top N 个能力"""
        all_caps = unified_capability_loader.load_all()
        if not all_caps:
            print("[Recommender] 没有加载到任何能力")
            return []

        # 第1步：关键词快速匹配
        keyword_results = self._keyword_match(user_input, all_caps, n)
        if keyword_results:
            print(f"[Recommender] 关键词匹配: {[r.get('name') for r in keyword_results]}")
            return keyword_results

        # 第2步：LLM推荐
        prompt = self._build_prompt(user_input, all_caps, types)
        print(f"[Recommender] 请求 LLM 推荐: {user_input[:50]}...")

        response_text = self.llm.generate(
            prompt=prompt,
            model=self.model,
            temperature=0.2,
            max_tokens=100,
            timeout=30,
            task_type="recommend"
        )

        if not response_text:
            print("[Recommender] LLM 返回空")
            return self._fallback_recommend(user_input, all_caps, n)

        print(f"[Recommender] LLM 响应: {response_text.strip()}")

        names = self._parse_recommendations(response_text)

        results = []
        for name in names:
            matched = self._fuzzy_match_capability(name, all_caps)
            if matched:
                results.append(matched)
                if len(results) >= n:
                    break

        if not results:
            results = self._fallback_recommend(user_input, all_caps, n)

        return results[:n]

    def recommend_with_cache(self, user_input: str, types: List[str] = None,
                             n: int = 3) -> List[Dict]:
        """带缓存的推荐"""
        clean_input = " ".join(user_input.strip().split())
        cache_key = hashlib.md5(
            f"{clean_input}:{str(types)}:{n}".encode()
        ).hexdigest()

        if cache_key in self._cache:
            cached_time, cached_result = self._cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                print(f"[Recommender] 命中缓存: {user_input[:30]}...")
                return cached_result

        result = self.recommend(user_input, types, n)
        self._cache[cache_key] = (time.time(), result)
        return result

    def clear_cache(self):
        self._cache.clear()
        print("[Recommender] 缓存已清空")

    def get_recommendation_prompt(self, user_input: str) -> str:
        """生成Agent推荐提示词（供Gateway使用）"""
        all_caps = unified_capability_loader.load_all()
        cap_list = "\n".join([
            f"- {name}: {cap.get('description', '')[:60]}"
            for name, cap in list(all_caps.items())[:25]
        ])
        return f"""用户输入：{user_input[:200]}

可用Agent：
{cap_list}

只输出最合适的Agent名称（一个词）："""

    # ====================================================================
    #  关键词匹配
    # ====================================================================

    def _keyword_match(self, user_input: str, all_caps: Dict,
                       n: int) -> List[Dict]:
        """关键词快速匹配，置信度够高时跳过LLM"""
        t = user_input.lower()
        scored = []

        for name, cap in all_caps.items():
            keywords = cap.get("keywords", [])
            description = cap.get("description", "")
            score = 0
            matched_kw = []

            for kw in keywords:
                if kw.lower() in t:
                    score += 1
                    matched_kw.append(kw)

            # 描述中的关键词也加分
            for word in description.lower().split():
                if len(word) >= 2 and word in t:
                    score += 0.3

            if score > 0:
                scored.append({
                    "name": name,
                    "score": score,
                    "matched": matched_kw,
                    "cap": cap
                })

        scored.sort(key=lambda x: x["score"], reverse=True)

        # 只有第一名分数 >= 2 才直接用关键词结果
        if scored and scored[0]["score"] >= 2:
            return [s["cap"] for s in scored[:n]]

        return []

    # ====================================================================
    #  LLM推荐
    # ====================================================================

    def _build_prompt(self, user_input: str, all_caps: Dict,
                      types: List[str] = None) -> str:
        prompt = f"""用户请求: {user_input}

请从以下能力中选择最合适的 3 个，按优先级排序。

可用能力列表（必须从中选择）:
"""
        sorted_caps = list(all_caps.items())[:30]
        for name, cap in sorted_caps:
            desc = cap.get('description', '')[:60]
            prompt += f"- {name}: {desc}\n"

        prompt += f"\n（共 {len(all_caps)} 个能力，已展示前 30 个）\n"
        prompt += """
请只输出能力名称，用逗号分隔，最多 3 个。
必须使用上面列表中的精确名称。

推荐结果:"""
        return prompt

    def _parse_recommendations(self, text: str) -> List[str]:
        """解析LLM返回的能力名称列表"""
        text = re.sub(r'推荐结果[:：]?', '', text)
        text = re.sub(r'推荐[:：]?', '', text)
        text = text.strip()

        names = re.split(r'[,，、\n]', text)

        cleaned = []
        for name in names:
            name = name.strip()
            name = re.sub(r'^\d+[\.、]\s*', '', name)
            name = re.sub(r'\s+', ' ', name)
            if name and len(name) < 60 and not name.startswith('```'):
                cleaned.append(name)
        return cleaned[:5]

    # ====================================================================
    #  模糊匹配 + 降级
    # ====================================================================

    def _fuzzy_match_capability(self, name: str, all_caps: Dict) -> Optional[Dict]:
        """模糊匹配能力名称"""
        name_lower = name.lower()
        for cap_name, cap_data in all_caps.items():
            if name_lower == cap_name.lower():
                return cap_data
            if name_lower in cap_name.lower() or cap_name.lower() in name_lower:
                return cap_data
        return None

    def _fallback_recommend(self, user_input: str, all_caps: Dict,
                            n: int) -> List[Dict]:
        """降级推荐：按关键词匹配兜底"""
        t = user_input.lower()
        scored = []
        for name, cap in all_caps.items():
            desc = cap.get("description", "").lower()
            score = sum(1 for word in t.split() if len(word) >= 2 and word in desc)
            if score > 0:
                scored.append((score, cap))
        scored.sort(key=lambda x: x[0], reverse=True)

        defaults = ["chat_agent", "code_agent", "analysis_agent"]
        results = [cap for _, cap in scored[:n]]
        if not results:
            for name in defaults:
                if name in all_caps:
                    results.append(all_caps[name])
                    if len(results) >= n:
                        break
        return results[:n]


# 全局实例
capability_recommender = CapabilityRecommender()
