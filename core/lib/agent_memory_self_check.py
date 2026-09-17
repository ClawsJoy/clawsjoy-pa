#!/usr/bin/env python3
"""Agent Memory Self Check - Agent Memory Self Check 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
from pathlib import Path
from typing import Dict, List, Optional

from api.skill_market import skill_recommender
from core.lib.knowledge_registry import knowledge_registry
from core.lib.memory import memory


class AgentMemorySelfCheck:
    """Agent 记忆自检器 - 主动检查技能、知识、记忆状态"""

    def __init__(self):
        self.skill_count = 0
        self.knowledge_count = 0
        self.memory_count = 0

    def refresh_stats(self):
        """刷新统计数据"""
        self.skill_count = self._get_skill_count()
        self.knowledge_count = self._get_knowledge_count()
        self.memory_count = self._get_memory_count()

    def _get_skill_count(self) -> int:
        try:
            return skill_recommender.collection.count()
        except Exception as e:
            return 0

    def _get_knowledge_count(self) -> int:
        try:
            stats = knowledge_registry.get_stats()
            return stats.get("total_knowledge", 0)
        except Exception as e:
            return 0

    def _get_memory_count(self) -> int:
        try:
            stats = memory.get_stats()
            return stats.get("total_memories", 0)
        except Exception as e:
            return 0

    def check_skill(self, skill_name: str) -> Dict:
        """检查特定技能是否存在"""
        try:
            results = skill_recommender.collection.get(where={"name": skill_name})
            if results.get("metadatas"):
                return {
                    "exists": True,
                    "skill": results["metadatas"][0],
                    "message": f"技能 {skill_name} 已注册",
                }
        except Exception as e:
            pass
        return {"exists": False, "message": f"技能 {skill_name} 未找到"}

    def search_skill(self, query: str, n: int = 5) -> List[Dict]:
        """语义搜索技能"""
        try:
            return skill_recommender.recommend(query, n)
        except Exception as e:
            return []

    def search_knowledge(self, query: str, n: int = 5) -> List[Dict]:
        """语义搜索知识"""
        try:
            return knowledge_registry.search(query, n=n)
        except Exception as e:
            return []

    def recall_memory(
        self, query: str, user_id: str = "default", n: int = 5
    ) -> List[str]:
        """召回用户记忆"""
        try:
            return memory.recall(query, user_id=user_id, n=n)
        except Exception as e:
            return []

    def get_stats(self) -> Dict:
        """获取完整统计"""
        self.refresh_stats()
        return {
            "skills": {
                "total": self.skill_count,
                "message": f"原子技能库: {self.skill_count} 个技能",
            },
            "knowledge": {
                "total": self.knowledge_count,
                "message": f"知识库: {self.knowledge_count} 条知识",
            },
            "memory": {
                "total": self.memory_count,
                "message": f"记忆库: {self.memory_count} 条记忆",
            },
            "status": (
                "healthy"
                if self.skill_count > 0 and self.knowledge_count > 0
                else "degraded"
            ),
        }

    def self_check_report(self) -> str:
        """生成自检报告"""
        self.refresh_stats()
        report = f"""
┌─────────────────────────────────────────────────────────────┐
│                    Agent 自检报告                           │
├─────────────────────────────────────────────────────────────┤
│  ✅ 原子技能库: {self.skill_count} 个技能
│  ✅ 知识库: {self.knowledge_count} 条知识
│  ✅ 记忆库: {self.memory_count} 条记忆
├─────────────────────────────────────────────────────────────┤
│  📊 总计: {self.skill_count + self.knowledge_count + self.memory_count} 条向量
└─────────────────────────────────────────────────────────────┘
"""
        return report


agent_memory_self_check = AgentMemorySelfCheck()
