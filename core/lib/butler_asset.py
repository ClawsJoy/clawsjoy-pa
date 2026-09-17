#!/usr/bin/env python3
"""Butler Asset - Butler Asset 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ButlerAsset:
    """管家数字资产 - 用户专属"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.asset_root = Path(f"data/users/{user_id}/butler_asset")
        self.asset_root.mkdir(parents=True, exist_ok=True)

        # 资产文件
        self.memory_file = self.asset_root / "memory.json"
        self.preference_file = self.asset_root / "preferences.json"
        self.knowledge_file = self.asset_root / "knowledge.json"
        self.achievement_file = self.asset_root / "achievements.json"

        # 加载资产
        self._load_assets()

    def _load_assets(self):
        """加载用户资产"""
        self.memory = self._load_json(self.memory_file, {})
        self.preferences = self._load_json(self.preference_file, {})
        self.knowledge = self._load_json(self.knowledge_file, {})
        self.achievements = self._load_json(self.achievement_file, [])

    def _load_json(self, file_path: Path, default):
        """加载 JSON 文件"""
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 确保 achievements 是列表
                    if file_path == self.achievement_file and not isinstance(
                        data, list
                    ):
                        return default
                    return data
            except Exception:
                return default
        return default

    def _save_json(self, file_path: Path, data):
        """保存 JSON 文件"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存资产失败: {e}")

    # 记忆资产
    def remember(self, key: str, value: Any) -> bool:
        """记住信息（记忆资产）"""
        self.memory[key] = {
            "value": value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self._save_json(self.memory_file, self.memory)
        return True

    def recall(self, key: str) -> Optional[Any]:
        """回忆信息"""
        return self.memory.get(key, {}).get("value")

    # 偏好资产
    def set_preference(self, key: str, value: Any) -> bool:
        """设置偏好（偏好资产）"""
        self.preferences[key] = value
        self._save_json(self.preference_file, self.preferences)
        return True

    def get_preference(self, key: str, default=None):
        """获取偏好"""
        return self.preferences.get(key, default)

    def get_all_preferences(self) -> Dict:
        """获取所有偏好"""
        return self.preferences

    # 知识资产
    def add_knowledge(self, category: str, key: str, value: Any) -> bool:
        """添加知识（知识资产）"""
        if category not in self.knowledge:
            self.knowledge[category] = {}
        self.knowledge[category][key] = value
        self._save_json(self.knowledge_file, self.knowledge)
        return True

    def get_knowledge(self, category: str, key: str = None):
        """获取知识"""
        if key:
            return self.knowledge.get(category, {}).get(key)
        return self.knowledge.get(category, {})

    # 成就资产
    def add_achievement(self, name: str, metadata: Dict = None) -> bool:
        """添加成就（成就资产）"""
        achievement = {
            "name": name,
            "earned_at": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self.achievements.append(achievement)
        self._save_json(self.achievement_file, self.achievements)
        return True

    def get_achievements(self) -> List[Dict]:
        """获取所有成就"""
        return self.achievements

    # 资产统计
    def get_asset_summary(self) -> Dict:
        """获取资产摘要"""
        return {
            "user_id": self.user_id,
            "memory_count": len(self.memory),
            "preferences_count": len(self.preferences),
            "knowledge_categories": len(self.knowledge),
            "achievements_count": len(self.achievements),
            "asset_root": str(self.asset_root),
        }


# 全局资产管理器实例（按用户）
_butler_assets: Dict[str, ButlerAsset] = {}


def get_butler_asset(user_id: str) -> ButlerAsset:
    """获取用户的管家资产（单例 per user）"""
    if user_id not in _butler_assets:
        _butler_assets[user_id] = ButlerAsset(user_id)
    return _butler_assets[user_id]
