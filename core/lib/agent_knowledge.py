#!/usr/bin/env python3
"""Agent Knowledge - Agent Knowledge 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""Agents 向量知识库 - 专门存储 Agents 学习内容"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class AgentKnowledgeBase:
    """Agents 专用知识库"""

    def __init__(self, knowledge_base_name: str = "agents_knowledge"):
        from core.lib.path_manager import path_manager

        self.persist_dir = Path(path_manager.get("data.vector_kb")) / knowledge_base_name
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        from core.lib.vector_knowledge_center import vector_knowledge_center

        self.client = vector_knowledge_center.client

        # 创建多个集合
        self.collections = {
            "reports": self.client.get_or_create_collection("reports"),
            "skills": self.client.get_or_create_collection("skills"),
            "agents_doc": self.client.get_or_create_collection("agents_doc"),
            "user_instructions": self.client.get_or_create_collection("user_instructions"),
            "learning_patterns": self.client.get_or_create_collection("learning_patterns"),
        }

        print(f"✅ Agents 知识库初始化完成")
        for name, col in self.collections.items():
            print(f"   - {name}: {col.count()} 条")

    def add_report(self, name: str, content: str, report_type: str, version: str):
        """添加报告到知识库"""
        doc_id = hashlib.md5(f"{name}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        self.collections["reports"].add(
            ids=[doc_id],
            documents=[content[:5000]],
            metadatas=[
                {
                    "name": name,
                    "type": report_type,
                    "version": version,
                    "date": datetime.now().isoformat(),
                    "category": "report",
                }
            ],
        )
        print(f"📚 报告已加入知识库: {name}")
        return doc_id

    def add_skill_doc(self, skill_name: str, description: str, usage: str, example: str = ""):
        """添加技能文档到知识库"""
        content = f"技能: {skill_name}\n描述: {description}\n用法: {usage}\n示例: {example}"
        doc_id = hashlib.md5(f"skill_{skill_name}".encode()).hexdigest()[:16]

        self.collections["skills"].add(
            ids=[doc_id],
            documents=[content[:3000]],
            metadatas=[
                {
                    "skill_name": skill_name,
                    "description": description,
                    "type": "skill_doc",
                    "date": datetime.now().isoformat(),
                }
            ],
        )
        print(f"🔧 技能文档已加入: {skill_name}")
        return doc_id

    def add_agent_doc(self, agent_name: str, capability: str, api_doc: str):
        """添加 Agent 文档到知识库"""
        content = f"Agent: {agent_name}\n能力: {capability}\nAPI: {api_doc}"
        doc_id = hashlib.md5(f"agent_{agent_name}".encode()).hexdigest()[:16]

        self.collections["agents_doc"].add(
            ids=[doc_id],
            documents=[content[:3000]],
            metadatas=[
                {
                    "agent_name": agent_name,
                    "capability": capability,
                    "type": "agent_doc",
                    "date": datetime.now().isoformat(),
                }
            ],
        )
        print(f"🤖 Agent 文档已加入: {agent_name}")
        return doc_id

    def add_learning_pattern(self, pattern: str, context: str, success: bool = True):
        """添加学习模式到知识库"""
        content = f"模式: {pattern}\n上下文: {context}\n结果: {'成功' if success else '失败'}"
        doc_id = hashlib.md5(f"pattern_{datetime.now().isoformat()}".encode()).hexdigest()[:16]

        self.collections["learning_patterns"].add(
            ids=[doc_id],
            documents=[content[:2000]],
            metadatas=[
                {
                    "pattern": pattern[:100],
                    "success": success,
                    "type": "learning_pattern",
                    "date": datetime.now().isoformat(),
                }
            ],
        )
        print(f"📖 学习模式已记录")
        return doc_id

    def search(self, query: str, collection: str = None, n: int = 5) -> List[Dict]:
        """搜索知识库"""
        results = []

        if collection and collection in self.collections:
            target_collections = [collection]
        else:
            target_collections = list(self.collections.keys())

        for col_name in target_collections:
            if col_name not in self.collections:
                continue
            try:
                result = self.collections[col_name].query(query_texts=[query], n_results=n)
                if result["documents"] and result["documents"][0]:
                    for i, doc in enumerate(result["documents"][0]):
                        results.append(
                            {
                                "collection": col_name,
                                "content": doc[:500],
                                "metadata": (result["metadatas"][0][i] if result["metadatas"] else {}),
                                "distance": (result["distances"][0][i] if result["distances"] else None),
                            }
                        )
            except Exception as e:
                print(f"⚠️ 搜索 {col_name} 失败: {e}")

        return sorted(results, key=lambda x: x.get("distance", 1))[:n]

    def get_stats(self) -> Dict:
        """获取知识库统计"""
        return {name: col.count() for name, col in self.collections.items()}


# 全局实例
agent_knowledge = AgentKnowledgeBase()
