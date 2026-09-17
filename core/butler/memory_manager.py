#!/usr/bin/env python3
"""Memory Manager - Memory Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import get_data_root

"""智能记忆管理器 - L0-L4 渐进式记忆"""
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MemoryItem:
    """记忆项"""

    content: str
    type: str  # conversation, preference, fact, todo
    importance: int  # 1-10
    timestamp: str
    context: Dict = None


class SmartMemoryManager:
    """智能记忆管理器"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.base_path = Path(f"{get_data_root()}/users/{user_id}/butler_memory")
        self.base_path.mkdir(parents=True, exist_ok=True)

        # 加载配置
        self._load_config()

        # 各层记忆
        self.l0_session: List[MemoryItem] = []  # 会话级
        self.l1_daily: List[MemoryItem] = []  # 日级
        self.l2_long: List[MemoryItem] = []  # 长期
        self.preferences: Dict = {}  # 偏好
        self.knowledge: Dict = {}  # 知识

        self._load()

    def _load_config(self):
        """加载配置"""
        import yaml

        config_file = Path("config/butler/butler.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {"features": {"memory": {"max_history": 50}}}

    def _load(self):
        """加载持久化数据"""
        # 加载偏好
        pref_file = self.base_path / "preferences.json"
        if pref_file.exists():
            with open(pref_file, "r") as f:
                self.preferences = json.load(f)

        # 加载知识
        knowledge_file = self.base_path / "knowledge.json"
        if knowledge_file.exists():
            with open(knowledge_file, "r") as f:
                self.knowledge = json.load(f)

        # 加载长期记忆
        long_file = self.base_path / "long_term.json"
        if long_file.exists():
            with open(long_file, "r") as f:
                data = json.load(f)
                self.l2_long = [MemoryItem(**item) for item in data]

    def _save(self):
        """保存持久化数据"""
        with open(self.base_path / "preferences.json", "w") as f:
            json.dump(self.preferences, f, indent=2, ensure_ascii=False)

        with open(self.base_path / "knowledge.json", "w") as f:
            json.dump(self.knowledge, f, indent=2, ensure_ascii=False)

        with open(self.base_path / "long_term.json", "w") as f:
            data = [asdict(item) for item in self.l2_long]
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_conversation(self, user_msg: str, assistant_msg: str):
        """添加对话到会话记忆"""
        item = MemoryItem(
            content=f"用户: {user_msg}\n管家: {assistant_msg}",
            type="conversation",
            importance=3,
            timestamp=datetime.now().isoformat(),
        )
        self.l0_session.append(item)

        # L0 达到上限后，压缩到 L1
        max_session = (
            self.config.get("features", {}).get("memory", {}).get("max_history", 50)
        )
        if len(self.l0_session) > max_session:
            self._compress_to_daily()

        self._save()

    def _compress_to_daily(self):
        """压缩会话记忆到日记忆"""
        # 提取重要信息
        for item in self.l0_session:
            if item.importance >= 5:
                self.l1_daily.append(item)

        # 日记忆上限
        if len(self.l1_daily) > 100:
            self._compress_to_long()

        self.l0_session = self.l0_session[-20:]  # 保留最近20条

    def _compress_to_long(self):
        """压缩日记忆到长期记忆"""
        # 提取高频、高重要性信息
        for item in self.l1_daily:
            if item.importance >= 7:
                self.l2_long.append(item)

        # 去重和合并
        self._deduplicate()

        self.l1_daily = []
        self._save()

    def _deduplicate(self):
        """去重"""
        seen = set()
        unique = []
        for item in self.l2_long:
            key = item.content[:100]
            if key not in seen:
                seen.add(key)
                unique.append(item)
        self.l2_long = unique[-500:]  # 保留最近500条

    def remember_preference(self, key: str, value: Any):
        """记住偏好"""
        self.preferences[key] = value
        self._save()

    def recall_preference(self, key: str) -> Optional[Any]:
        """回忆偏好"""
        return self.preferences.get(key)

    def remember_fact(self, fact: str, importance: int = 5):
        """记住事实"""
        item = MemoryItem(
            content=fact,
            type="fact",
            importance=importance,
            timestamp=datetime.now().isoformat(),
        )
        self.l2_long.append(item)
        self._save()

    def recall_context(self, query: str, limit: int = 5) -> List[str]:
        """回忆相关上下文"""
        results = []

        # 从会话记忆检索
        for item in reversed(self.l0_session):
            if query in item.content and len(results) < limit:
                results.append(item.content)

        # 从长期记忆检索
        if len(results) < limit:
            for item in reversed(self.l2_long):
                if query in item.content and len(results) < limit:
                    results.append(item.content)

        return results

    def get_conversation_context(self, limit: int = 10) -> List[Dict]:
        """获取对话上下文"""
        contexts = []
        for item in self.l0_session[-limit:]:
            if item.type == "conversation":
                contexts.append({"content": item.content, "timestamp": item.timestamp})
        return contexts

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "session_count": len(self.l0_session),
            "daily_count": len(self.l1_daily),
            "long_term_count": len(self.l2_long),
            "preferences_count": len(self.preferences),
            "knowledge_count": len(self.knowledge),
        }


    def store_data(self, key: str, value: Any) -> bool:
        """存储任意数据（使用 preference 存储）"""
        return self.remember_preference(key, value)
    
    def load_data(self, key: str, default=None) -> Any:
        """加载数据"""
        value = self.recall_preference(key)
        return value if value is not None else default
    
    def delete_data(self, key: str) -> bool:
        """删除数据"""
        try:
            # 获取当前偏好
            prefs = getattr(self, '_preferences', {})
            if key in prefs:
                del prefs[key]
                setattr(self, '_preferences', prefs)
                self._save()
                return True
        except Exception as e:
            pass
        return False
    
    def list_data(self) -> list:
        """列出所有数据键"""
        prefs = getattr(self, '_preferences', {})
        return list(prefs.keys())
