#!/usr/bin/env python3
"""Experience Decider - Experience Decider 模块

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

"""
经验决策器 - 让 learning_patterns 驱动决策
整合 decision_evaluator, priority_adjuster, self_tuner
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ExperienceDecider:
    """经验决策器 - 基于历史经验影响决策"""

    def __init__(self):
        self.knowledge_file = Path(f"{get_data_root()}/agent_knowledge.json")
        self.learning_patterns_collection = None
        self._init_knowledge()

    def _init_knowledge(self):
        """初始化知识库连接"""
        try:
            import chromadb
            from chromadb.config import Settings
            from chromadb.utils import embedding_functions

            # #30 修复: 默认库复用 VectorKnowledgeCenter 的 client(同 settings),
            # 避免同路径不同 settings 触发 "An instance of Chroma already exists"
            from core.lib.vector_knowledge_center import vector_knowledge_center as _vkc

            self.client = _vkc.get_client()
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

            # 获取或创建 learning_patterns 集合
            try:
                self.learning_patterns_collection = self.client.get_collection("learning_patterns")
            except Exception as e:
                self.learning_patterns_collection = self.client.create_collection(
                    name="learning_patterns", embedding_function=self.embedding_fn
                )
        except Exception as e:
            print(f"⚠️ 知识库连接失败: {e}")
            self.learning_patterns_collection = None

    def query_similar_experiences(self, task: str, limit: int = 5) -> List[Dict]:
        """查询相似任务的历史经验"""
        if not self.learning_patterns_collection:
            return []

        try:
            results = self.learning_patterns_collection.query(query_texts=[task], n_results=limit)

            experiences = []
            if results["metadatas"]:
                for meta in results["metadatas"][0]:
                    experiences.append(meta)
            return experiences
        except Exception as e:
            print(f"⚠️ 查询失败: {e}")
            return []

    def get_success_rate_for_skill(self, skill_name: str) -> float:
        """获取技能的历史成功率"""
        experiences = self.query_similar_experiences(skill_name, limit=20)
        if not experiences:
            return 0.5  # 无历史数据，中等置信度

        success_count = sum(1 for e in experiences if e.get("success", False))
        return success_count / len(experiences)

    def adjust_priority(self, task: str, current_priority: int) -> int:
        """根据历史经验调整优先级"""
        similar = self.query_similar_experiences(task, limit=10)
        if not similar:
            return current_priority

        # 计算相似任务的平均成功率
        success_rate = sum(1 for e in similar if e.get("success", False)) / len(similar)

        # 高成功率任务提权，低成功率降权
        if success_rate > 0.8:
            return max(1, current_priority - 10)
        elif success_rate < 0.3:
            return min(100, current_priority + 20)

        return current_priority

    def should_auto_retry(self, skill_name: str, failure_count: int) -> bool:
        """判断是否应该自动重试"""
        success_rate = self.get_success_rate_for_skill(skill_name)

        # 成功率高时自动重试，成功率低时跳过
        if success_rate > 0.7 and failure_count < 3:
            return True
        return False

    def record_experience(self, task: str, action: str, result: Dict, context: Dict = None):
        """记录经验到 learning_patterns"""
        if not self.learning_patterns_collection:
            return

        import hashlib

        doc_id = hashlib.md5(f"{task}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]

        success = result.get("success", False)
        error = result.get("error", "") if not success else ""

        metadata = {
            "task": task[:200],
            "action": action,
            "success": success,
            "error": error[:100] if error else "",
            "timestamp": datetime.now().isoformat(),
            "type": "experience",
        }

        if context:
            metadata["context"] = json.dumps(context)[:200]

        document = f"任务: {task}\n动作: {action}\n结果: {'成功' if success else '失败'}"
        if error:
            document += f"\n错误: {error}"

        try:
            self.learning_patterns_collection.upsert(ids=[doc_id], documents=[document], metadatas=[metadata])
            print(f"📝 经验已记录: {task[:50]}...")
        except Exception as e:
            print(f"⚠️ 记录失败: {e}")

    def get_recommendation(self, task: str) -> Dict:
        """获取任务执行建议"""
        similar = self.query_similar_experiences(task, limit=5)

        if not similar:
            return {
                "has_experience": False,
                "recommendation": "无历史经验，建议谨慎执行",
                "confidence": 0.0,
            }

        success_count = sum(1 for e in similar if e.get("success", False))
        success_rate = success_count / len(similar)

        # 找出最成功的动作
        action_counts = defaultdict(int)
        for e in similar:
            action_counts[e.get("action", "unknown")] += 1
        best_action = max(action_counts, key=action_counts.get) if action_counts else None

        if success_rate > 0.8:
            recommendation = f"建议执行，历史成功率 {success_rate*100:.0f}%"
            confidence = success_rate
        elif success_rate > 0.5:
            recommendation = f"可尝试执行，历史成功率 {success_rate*100:.0f}%"
            confidence = success_rate
        else:
            recommendation = f"建议人工介入，历史成功率较低 ({success_rate*100:.0f}%)"
            confidence = 0.3

        return {
            "has_experience": True,
            "recommendation": recommendation,
            "confidence": confidence,
            "success_rate": success_rate,
            "similar_count": len(similar),
            "best_action": best_action,
            "sample_experiences": similar[:3],
        }

    def get_stats(self) -> Dict:
        """获取统计信息"""
        if not self.learning_patterns_collection:
            return {"status": "disconnected", "total_experiences": 0}

        try:
            count = self.learning_patterns_collection.count()
            return {
                "status": "connected",
                "total_experiences": count,
                "collection": "learning_patterns",
            }
        except Exception as e:
            return {"status": "error", "total_experiences": 0}


# 全局实例
_experience_decider = None


def get_experience_decider():
    global _experience_decider
    if _experience_decider is None:
        _experience_decider = ExperienceDecider()
    return _experience_decider
