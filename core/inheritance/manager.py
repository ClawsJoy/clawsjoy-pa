#!/usr/bin/env python3
"""Manager - Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import Experience
from .storage import ExperienceStorage


class InheritanceManager:
    """传承管理器 - 管理经验的沉淀、继承、进化"""

    VERSION = "1.0.0"

    def __init__(self, user_id: str = "default", agent_name: str = "base"):
        self.user_id = user_id
        self.agent_name = agent_name
        self.storage = ExperienceStorage(user_id, agent_name)
        self._load_config()

    def _load_config(self):
        """加载配置"""
        from pathlib import Path

        import yaml

        config_file = Path("config/inheritance.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {
                "inheritance": {
                    "sedimentation": {"min_confidence": 0.6, "min_usage": 5},
                    "generation": {"decay_rate": 0.9, "max_generations": 10},
                }
            }

    def learn(
        self,
        exp_type: str,
        content: Dict,
        confidence: float = 0.5,
        tags: List[str] = None,
    ) -> Experience:
        """学习新经验"""
        exp = Experience(
            type=exp_type,
            content=content,
            confidence=confidence,
            source="learning",
            tags=tags or [],
        )
        self.storage.save_experience(exp)
        print(f"📚 学习新经验: {exp_type} (置信度: {confidence})")
        return exp

    def inherit(self, parent_exp: Experience, adapter: Dict = None) -> Experience:
        """继承经验"""
        # 继承时内容可以适配
        content = parent_exp.content.copy()
        if adapter:
            content.update(adapter)

        # 继承时置信度衰减
        decay_rate = (
            self.config.get("inheritance", {})
            .get("generation", {})
            .get("decay_rate", 0.9)
        )
        new_confidence = parent_exp.confidence * decay_rate

        # 创建新经验（不指定id，让系统自动生成）
        exp = Experience(
            type=parent_exp.type,
            content=content,
            confidence=new_confidence,
            source="inherited",
            source_id=parent_exp.source_id,
            parent_id=parent_exp.id,
            version=parent_exp.version + 1,
            tags=parent_exp.tags.copy(),
        )
        self.storage.save_experience(exp)

        # 创建传承链
        self.storage.create_chain(parent_exp.id)
        self.storage.add_to_chain(f"chain_{parent_exp.id}", exp.id)

        print(
            f"🔗 继承经验: {parent_exp.type} -> {exp.type} (置信度: {parent_exp.confidence} -> {new_confidence})"
        )
        return exp

    def reinforce(self, exp_id: str, success: bool):
        """强化经验"""
        self.storage.record_usage(exp_id, success)
        exp = self.storage.get_experience(exp_id)
        if exp:
            print(f"💪 强化经验: {exp.type} (成功率: {exp.success_rate:.2f})")

    def get_best(self, exp_type: str = None) -> Optional[Experience]:
        """获取最佳经验"""
        experiences = self.storage.list_experiences(exp_type, min_confidence=0.3)
        if experiences:
            return max(experiences, key=lambda e: e.confidence)
        return None

    def get_inheritance_chain(self, exp_id: str) -> List[Experience]:
        """获取传承链"""
        chain = []
        current_id = exp_id
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            current = self.storage.get_experience(current_id)
            if current:
                chain.append(current)
                current_id = current.parent_id
            else:
                break

        return chain

    def sediment(self):
        """经验沉淀"""
        experiences = self.storage.list_experiences()
        min_confidence = (
            self.config.get("inheritance", {})
            .get("sedimentation", {})
            .get("min_confidence", 0.6)
        )
        min_usage = (
            self.config.get("inheritance", {})
            .get("sedimentation", {})
            .get("min_usage", 5)
        )

        sedimented = []
        for exp in experiences:
            if exp.success_rate >= min_confidence and exp.use_count >= min_usage:
                if exp.type != "wisdom":
                    exp.type = "wisdom"
                    exp.confidence = min(exp.confidence + 0.1, 1.0)
                    self.storage.save_experience(exp)
                    sedimented.append(exp)

        if sedimented:
            print(f"🧠 经验沉淀: {len(sedimented)} 个经验升级为智慧")

        return sedimented

    def get_stats(self) -> Dict:
        """获取统计信息"""
        experiences = self.storage.list_experiences()
        return {
            "total_experiences": len(experiences),
            "by_type": {
                t: len([e for e in experiences if e.type == t])
                for t in set(e.type for e in experiences)
            },
            "avg_confidence": (
                sum(e.confidence for e in experiences) / len(experiences)
                if experiences
                else 0
            ),
            "total_uses": sum(e.use_count for e in experiences),
            "total_successes": sum(e.success_count for e in experiences),
        }
