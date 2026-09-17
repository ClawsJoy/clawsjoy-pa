#!/usr/bin/env python3
"""Dialect Learner - Dialect Learner 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class DialectLearner:
    """方言学习器 - 存储用户方言映射"""

    def __init__(self):
        self.storage_file = Path("data/dialect_mappings.json")
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        """加载映射库"""
        if self.storage_file.exists():
            with open(self.storage_file, "r") as f:
                self.mappings = json.load(f)
        else:
            self.mappings = {
                "user_mappings": {},  # 用户级映射
                "global_mappings": {},  # 全局映射
                "learning_history": [],  # 学习历史
            }

    def _save(self):
        """保存映射库"""
        with open(self.storage_file, "w") as f:
            json.dump(self.mappings, f, indent=2, ensure_ascii=False)

    def learn(self, user_id: str, dialect_word: str, standard_word: str):
        """学习方言映射"""
        if user_id not in self.mappings["user_mappings"]:
            self.mappings["user_mappings"][user_id] = {}

        self.mappings["user_mappings"][user_id][dialect_word] = {
            "standard": standard_word,
            "learned_at": datetime.now().isoformat(),
            "use_count": 1,
        }

        # 记录学习历史
        self.mappings["learning_history"].append(
            {
                "user_id": user_id,
                "dialect": dialect_word,
                "standard": standard_word,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # 如果同一词汇被多个用户学习，提升为全局
        self._promote_to_global(dialect_word, standard_word)

        self._save()
        print(f"📚 学习方言: {dialect_word} -> {standard_word}")

    def translate(self, user_id: str, text: str) -> str:
        """翻译方言文本"""
        result = text
        user_mappings = self.mappings["user_mappings"].get(user_id, {})
        global_mappings = self.mappings["global_mappings"]

        # 合并用户映射和全局映射（用户优先）
        all_mappings = {**global_mappings, **user_mappings}

        for dialect, info in all_mappings.items():
            if dialect in result:
                standard = info if isinstance(info, str) else info.get("standard", info)
                result = result.replace(dialect, standard)

        return result

    def _promote_to_global(self, dialect_word: str, standard_word: str):
        """提升为全局映射（被多个用户学习）"""
        # 统计使用次数
        use_count = 0
        for user_maps in self.mappings["user_mappings"].values():
            if dialect_word in user_maps:
                use_count += 1

        if use_count >= 3 and dialect_word not in self.mappings["global_mappings"]:
            self.mappings["global_mappings"][dialect_word] = standard_word
            print(f"🌟 方言已提升为全局: {dialect_word} -> {standard_word}")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_mappings": len(self.mappings["global_mappings"]),
            "user_mappings": sum(
                len(v) for v in self.mappings["user_mappings"].values()
            ),
            "learning_count": len(self.mappings["learning_history"]),
        }


dialect_learner = DialectLearner()
