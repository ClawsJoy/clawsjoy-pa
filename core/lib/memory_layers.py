#!/usr/bin/env python3
"""Memory Layers - Memory Layers 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""四层记忆架构实现"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from core.lib.memory_vector import vector_memory
from core.lib.memory_vector import vector_memory as memory


class MemoryLayers:
    """四层记忆系统"""

    def __init__(self):
        self.memory_dir = Path("memory")
        self.daily_dir = self.memory_dir / "daily"
        self.long_term_file = self.memory_dir / "MEMORY.md"

        # 创建目录
        self.daily_dir.mkdir(parents=True, exist_ok=True)

    # ========== L0: 会话层 ==========
    def add_session_memory(self, session_id, user_input, response):
        """添加会话记忆"""
        session_file = self.memory_dir / f"session_{session_id}.json"
        sessions = self._load_json(session_file)
        sessions.append(
            {
                "timestamp": datetime.now().isoformat(),
                "user": user_input,
                "assistant": response,
            }
        )
        # 只保留最近 50 条
        if len(sessions) > 50:
            sessions = sessions[-50:]
        self._save_json(session_file, sessions)
        return True

    def get_session_memory(self, session_id, limit=10):
        """获取会话记忆"""
        session_file = self.memory_dir / f"session_{session_id}.json"
        sessions = self._load_json(session_file)
        return sessions[-limit:]

    # ========== L1: 日记忆层 ==========
    def add_daily_memory(self, content, category="general"):
        """添加日记忆（append-only）"""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_file = self.daily_dir / f"{today}.md"

        timestamp = datetime.now().strftime("%H:%M:%S")
        with open(daily_file, "a", encoding="utf-8") as f:
            f.write(f"- [{timestamp}] [{category}] {content}\n")
        return True

    def get_daily_memory(self, days=7):
        """获取最近 N 天的日记忆"""
        memories = []
        for d in range(days):
            date = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
            daily_file = self.daily_dir / f"{date}.md"
            if daily_file.exists():
                with open(daily_file, "r", encoding="utf-8") as f:
                    memories.append({"date": date, "content": f.read()})
        return memories

    # ========== L2: 长期记忆层 ==========
    def add_long_term_memory(self, content, importance="normal"):
        """添加长期记忆（经筛选的持久知识）"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self.long_term_file, "a", encoding="utf-8") as f:
            f.write(f"\n## {timestamp} [{importance}]\n{content}\n")

        # 同时存入 brain_v2.json
        memory.remember(content, category="long_term")
        return True

    def get_long_term_memory(self, limit=20):
        """获取长期记忆"""
        if not self.long_term_file.exists():
            return []

        with open(self.long_term_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 解析 markdown 格式的记忆
        memories = []
        for section in content.split("\n## "):
            if section.strip():
                lines = section.split("\n", 1)
                if len(lines) == 2:
                    memories.append({"title": lines[0], "content": lines[1][:200]})
        return memories[-limit:]

    # ========== L3: 向量层 ==========
    def add_vector_memory(self, text, category="general"):
        """添加向量记忆"""
        return vector_memory.add(text, category=category)

    def search_vector_memory(self, query, n=5):
        """搜索向量记忆"""
        return vector_memory.search(query, n=n)

    # ========== 辅助方法 ==========
    def _load_json(self, file_path):
        if file_path.exists():
            with open(file_path, "r") as f:
                return json.load(f)
        return []

    def _save_json(self, file_path, data):
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    # ========== 记忆晋升 ==========
    def promote_to_long_term(self, days_threshold=7):
        """将重要的日记忆晋升为长期记忆"""
        recent_daily = self.get_daily_memory(days=days_threshold)

        for daily in recent_daily:
            # 简单规则：超过 500 字或包含重要关键词
            content = daily.get("content", "")
            if len(content) > 500 or any(
                kw in content for kw in ["重要", "成功", "经验"]
            ):
                self.add_long_term_memory(
                    f"从 {daily['date']} 日记忆晋升:\n{content[:500]}",
                    importance="promoted",
                )
        return True

    # ========== 统计 ==========
    def get_stats(self):
        """获取记忆统计"""
        daily_count = len(list(self.daily_dir.glob("*.md")))

        # 向量统计
        vector_stats = vector_memory.get_stats()

        return {
            "session": "动态",
            "daily_files": daily_count,
            "long_term": self.long_term_file.exists(),
            "vector_count": vector_stats.get("total_vectors", 0),
        }


memory_layers = MemoryLayers()
