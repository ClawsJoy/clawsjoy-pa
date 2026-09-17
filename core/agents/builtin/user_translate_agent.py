#!/usr/bin/env python3
"""User Translate Agent - User Translate Agent 模块

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

"""用户可创建的语言大师实例 - 每个用户独立的翻译助手"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.agents.translate_agent import translate_agent as base_translator


class UserTranslateAgent:
    """
    用户自己的语言大师实例
    每个用户可以创建独立实例，有自己的学习记忆和偏好
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.user_dir = Path(
            funified_config.get("paths.users_dir", f"{get_data_root()}/users/")
            + "/{user_id}/translate_agent"
        )
        self.user_dir.mkdir(parents=True, exist_ok=True)

        self._load_user_memory()
        print(f"🔤 用户语言大师已创建: {user_id}")
        print(f"   📚 自定义词汇: {len(self.custom_vocab)} 条")

    def _load_user_memory(self):
        """加载用户自己的翻译记忆"""
        memory_file = self.user_dir / "memory.json"
        if memory_file.exists():
            with open(memory_file, "r") as f:
                data = json.load(f)
                self.custom_vocab = data.get("custom_vocab", {})
                self.translation_history = data.get("history", [])
                self.preferences = data.get("preferences", {})
        else:
            self.custom_vocab = {}
            self.translation_history = []
            self.preferences = {"style": "concise"}
        self._save_memory()

    def _save_memory(self):
        """保存用户记忆"""
        memory_file = self.user_dir / "memory.json"
        with open(memory_file, "w") as f:
            json.dump(
                {
                    "custom_vocab": self.custom_vocab,
                    "history": self.translation_history[-100:],
                    "preferences": self.preferences,
                    "updated_at": datetime.now().isoformat(),
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

    def add_custom_word(self, chinese: str, english: str):
        """添加自定义词汇"""
        self.custom_vocab[chinese] = english
        self._save_memory()
        print(f"📚 用户 {self.user_id} 添加词汇: {chinese} → {english}")

    def translate(self, query: str) -> Dict:
        """翻译查询（使用用户自己的词汇）"""
        # 先使用基础翻译
        result = base_translator.translate_query(query)

        # 应用用户自定义词汇覆盖
        for cn, en in self.custom_vocab.items():
            if cn in query:
                if en not in result["keywords"]:
                    result["keywords"].append(en)

        # 记录历史
        self.translation_history.append(
            {
                "query": query,
                "result": result["keywords"],
                "timestamp": datetime.now().isoformat(),
            }
        )
        self._save_memory()

        return {
            "user_id": self.user_id,
            "original": query,
            "keywords": result["keywords"],
            "skills": result["skills"],
            "custom_vocab_used": [cn for cn in self.custom_vocab.keys() if cn in query],
        }

    def get_stats(self) -> Dict:
        return {
            "user_id": self.user_id,
            "custom_vocab_size": len(self.custom_vocab),
            "history_count": len(self.translation_history),
            "preferences": self.preferences,
        }


# 用户实例缓存
_user_instances = {}


def get_user_translator(user_id: str) -> UserTranslateAgent:
    """获取或创建用户的语言大师实例（镜像）"""
    if user_id not in _user_instances:
        _user_instances[user_id] = UserTranslateAgent(user_id)
    return _user_instances[user_id]
