#!/usr/bin/env python3
"""Orchestrator 优化版 - 并行执行 + 缓存 + 可配置阈值"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.lib.engine_metrics import engine_metrics
from core.lib.unified_config import unified_config


@dataclass
class RouteResult:
    """路由结果"""

    intent: str
    confidence: float
    source: str
    duration_ms: float


class OptimizedOrchestratorV6:
    """优化版智能体编排器 - 并行四引擎 + 缓存"""

    # 类级别缓存，避免重复导入
    _llm_engine = None
    _vector_center = None
    _config_engine = None
    _rule_engine = None
    _loaded = False

    def __init__(self, user_id: str = "anonymous"):
        self.user_id = user_id
        self._intent_map = None
        self._route_stats = {
            "total": 0,
            "llm_hits": 0,
            "vector_hits": 0,
            "config_hits": 0,
            "rule_hits": 0,
            "cache_hits": 0,
            "avg_time_ms": 0,
        }
        self._load_engines()

        # 从配置读取阈值
        self.confidence_thresholds = {
            "llm": unified_config.get("orchestrator.llm_threshold", 0.3),
            "vector": unified_config.get("orchestrator.vector_threshold", 0.3),
            "config": unified_config.get("orchestrator.config_threshold", 0.2),
            "rule": unified_config.get("orchestrator.rule_threshold", 0.0),
        }

        # 并行执行开关
        self.parallel_mode = unified_config.get("orchestrator.parallel_mode", False)

        # 结果缓存
        self._result_cache = {}
        self._cache_ttl = unified_config.get("orchestrator.cache_ttl", 300)

    def _load_engines(self):
        """延迟加载引擎（只加载一次）"""
        if OptimizedOrchestratorV6._loaded:
            return

        try:
            from core.lib.vector_knowledge_center import vector_knowledge_center
            from engine.semantic.engines.config_engine import config_engine
            from engine.semantic.engines.llm_engine import llm_engine
            from engine.semantic.engines.rule_engine import rule_engine

            OptimizedOrchestratorV6._llm_engine = llm_engine
            OptimizedOrchestratorV6._vector_center = vector_knowledge_center
            OptimizedOrchestratorV6._config_engine = config_engine
            OptimizedOrchestratorV6._rule_engine = rule_engine
            OptimizedOrchestratorV6._loaded = True
            print("[Orchestrator] 引擎加载完成（优化版）")
        except Exception as e:
            print(f"[Orchestrator] 引擎加载失败: {e}")

    @lru_cache(maxsize=100)
    def _cached_llm_understand(self, message: str) -> Tuple[Optional[str], float]:
        """带缓存的 LLM 理解"""
        try:
            if self._llm_engine and self._llm_engine.is_available():
                intent, conf, _ = self._llm_engine.understand(message)
                return intent, conf
        except Exception:
            pass
        return None, 0.0

    def _llm_understand(self, message: str) -> Tuple[Optional[str], float, str]:
        """LLM 引擎理解"""
        start = time.time()
        intent, conf = self._cached_llm_understand(message)
        duration = (time.time() - start) * 1000

        if intent and conf > self.confidence_thresholds["llm"]:
            return intent, conf, "llm"
        return None, conf, "llm"

    def _vector_understand(self, message: str) -> Tuple[Optional[str], float, str]:
        """向量引擎理解"""
        start = time.time()
        try:
            if self._vector_center:
                skills_collection = self._vector_center.collections.get("skills")
                if skills_collection:
                    results = skills_collection.query(
                        query_texts=[message], n_results=3
                    )
                    if results and results.get("metadatas") and results["metadatas"][0]:
                        meta = results["metadatas"][0][0]
                        intent = meta.get("name", "unknown")
                        dist = (
                            results["distances"][0][0]
                            if results.get("distances")
                            else 1
                        )
                        conf = 1 - min(dist, 1.0)
                        if conf > self.confidence_thresholds["vector"]:
                            return intent, conf, "vector"
        except Exception:
            pass
        return None, 0, "vector"

    def _config_understand(self, message: str) -> Tuple[Optional[str], float, str]:
        """配置引擎理解"""
        start = time.time()
        try:
            if self._config_engine:
                intent, conf, _ = self._config_engine.understand(message)
                if conf > self.confidence_thresholds["config"]:
                    return intent, conf, "config"
        except Exception:
            pass
        return None, 0, "config"

    def _rule_understand(self, message: str) -> Tuple[str, float, str]:
        """规则引擎理解（兜底）"""
        try:
            if self._rule_engine:
                intent, conf, _ = self._rule_engine.understand(message)
                return intent, conf, "rule"
        except Exception:
            pass
        return "unknown", 0, "rule"

    def _get_intent_map(self) -> Dict:
        """获取意图映射"""
        if self._intent_map is not None:
            return self._intent_map

        capabilities = unified_config.get("keywords.agent_capabilities", {})
        intent_map = {}
        for agent_name in capabilities.keys():
            base_name = agent_name.replace("_agent", "").replace("_skill", "")
            intent_map[base_name] = agent_name
            intent_map[agent_name] = agent_name

        extra_map = {
            "weather": "weather_skill",
            "translate": "translate_agent",
            "code": "code_agent",
            "video": "video_agent",
            "analysis": "analysis_agent",
            "memory": "memory_agent",
            "greeting": "chat_agent",
            "thanks": "chat_agent",
            "farewell": "chat_agent",
            "calculate": "calculator",
        }
        intent_map.update(extra_map)
        self._intent_map = intent_map
        return intent_map

    def _intent_to_agent(self, intent: str) -> str:
        """意图转 Agent 名称"""
        intent_map = self._get_intent_map()
        if intent in intent_map:
            return intent_map[intent]
        if intent + "_agent" in intent_map:
            return intent + "_agent"
        return "chat_agent"

    def _social_route_check(self, message: str) -> Optional[str]:
        """社会协作路由检查"""
        social_keywords = [
            "分析",
            "报告",
            "统计",
            "数据",
            ".png",
            ".jpg",
            ".json",
            ".yaml",
        ]
        if any(kw in message.lower() for kw in social_keywords):
            print(f"[Orchestrator] 社会协作: 分析请求 → analysis_agent")
            return "analysis_agent"
        return None

    def smart_route_parallel(self, message: str) -> str:
        """并行执行四引擎"""
        start = time.time()

        # 1. 社会协作优先
        social_result = self._social_route_check(message)
        if social_result:
            self._record_route("social", (time.time() - start) * 1000)
            return social_result

        # 2. 检查缓存
        cache_key = f"{self.user_id}:{message}"
        if cache_key in self._result_cache:
            cached_time, cached_result = self._result_cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                self._route_stats["cache_hits"] += 1
                print(f"[Orchestrator] 缓存命中: {cached_result}")
                return cached_result

        # 3. 并行执行四个引擎
        engines = [
            (self._llm_understand, "llm"),
            (self._vector_understand, "vector"),
            (self._config_understand, "config"),
        ]

        # 规则引擎作为兜底，单独处理
        best_result = None
        best_confidence = 0

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(func, message): name for func, name in engines}

            for future in as_completed(futures):
                name = futures[future]
                try:
                    intent, conf, source = future.result(timeout=2)
                    if intent and conf > best_confidence:
                        best_result = (intent, conf, source)
                        best_confidence = conf
                        if conf > self.confidence_thresholds.get(name, 0.3):
                            # 足够高，可以提前返回
                            for f in futures:
                                f.cancel()
                            agent = self._intent_to_agent(intent)
                            self._record_route(source, (time.time() - start) * 1000)
                            self._result_cache[cache_key] = (time.time(), agent)
                            return agent
                except Exception:
                    continue

        # 4. 规则引擎兜底
        intent, conf, source = self._rule_understand(message)
        agent = self._intent_to_agent(intent)

        # 记录最佳结果（如果有）
        if best_result and best_confidence > conf:
            intent, conf, source = best_result
            agent = self._intent_to_agent(intent)

        self._record_route(source, (time.time() - start) * 1000)
        self._result_cache[cache_key] = (time.time(), agent)

        print(f"[Orchestrator] {source}: {intent}({conf:.2f})")
        return agent

    def smart_route(self, message: str) -> str:
        """智能路由（兼容原接口）"""
        if self.parallel_mode:
            return self.smart_route_parallel(message)
        return self.smart_route_serial(message)

    def smart_route_serial(self, message: str) -> str:
        """串行执行（原逻辑，用于对比测试）"""
        start = time.time()

        social_result = self._social_route_check(message)
        if social_result:
            self._record_route("social", (time.time() - start) * 1000)
            return social_result

        intent, conf, source = self._llm_understand(message)
        if intent:
            self._record_route(source, (time.time() - start) * 1000)
            return self._intent_to_agent(intent)

        intent, conf, source = self._vector_understand(message)
        if intent:
            self._record_route(source, (time.time() - start) * 1000)
            return self._intent_to_agent(intent)

        intent, conf, source = self._config_understand(message)
        if intent:
            self._record_route(source, (time.time() - start) * 1000)
            return self._intent_to_agent(intent)

        intent, conf, source = self._rule_understand(message)
        self._record_route(source, (time.time() - start) * 1000)
        return self._intent_to_agent(intent)

    def _record_route(self, route_type: str, duration_ms: float):
        """记录路由统计"""
        self._route_stats["total"] += 1
        hit_key = f"{route_type}_hits"
        if hit_key in self._route_stats:
            self._route_stats[hit_key] += 1

        total = self._route_stats["total"]
        old_avg = self._route_stats["avg_time_ms"]
        self._route_stats["avg_time_ms"] = (
            old_avg + (duration_ms - old_avg) / total if total > 0 else duration_ms
        )

        engine_metrics.record(route_type, True, duration_ms)

    def get_route_stats(self) -> dict:
        """获取路由统计"""
        stats = self._route_stats.copy()
        stats["cache_size"] = len(self._result_cache)
        stats["parallel_mode"] = self.parallel_mode
        return stats

    def clear_cache(self):
        """清除路由缓存"""
        self._result_cache.clear()
        self._cached_llm_understand.cache_clear()
        print("[Orchestrator] 缓存已清除")


# 兼容原接口
class OrchestratorAgent(OptimizedOrchestratorV6):
    pass


orchestrator = OptimizedOrchestratorV6()
