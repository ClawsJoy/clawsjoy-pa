#!/usr/bin/env python3
"""User Dialect Profile - User Dialect Profile 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class UserDialectProfile:
    """用户方言画像"""

    def __init__(self):
        self.profiles_dir = Path("data/users")
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def _get_profile_path(self, user_id: str) -> Path:
        return self.profiles_dir / user_id / "dialect_profile.json"

    def get_profile(self, user_id: str) -> Dict:
        """获取用户方言画像"""
        profile_path = self._get_profile_path(user_id)
        if profile_path.exists():
            with open(profile_path, "r") as f:
                return json.load(f)
        return {
            "user_id": user_id,
            "location": None,
            "dialect": None,
            "learned_words": {},
            "usage_count": {},
            "learning_history": [],
            "confidence": {},
        }

    def save_profile(self, user_id: str, profile: Dict):
        """保存用户方言画像"""
        profile_path = self._get_profile_path(user_id)
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile["updated_at"] = datetime.now().isoformat()
        with open(profile_path, "w") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

    def set_location(self, user_id: str, location: str):
        """设置用户地点"""
        profile = self.get_profile(user_id)
        profile["location"] = location
        # 根据地点自动判断方言
        dialect = self._detect_dialect_by_location(location)
        if dialect:
            profile["dialect"] = dialect
        self.save_profile(user_id, profile)
        return dialect

    def _detect_dialect_by_location(self, location: str) -> Optional[str]:
        """根据地点判断方言"""
        from pathlib import Path

        import yaml

        config_file = Path("config/dialect_learning.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
                dialects = config.get("dialects", {})
                for dialect, info in dialects.items():
                    for region in info.get("region", []):
                        if region in location or location in region:
                            return dialect
        return None

    def learn_word(
        self, user_id: str, dialect: str, standard: str, context: str = ""
    ) -> Dict:
        """学习方言词"""
        profile = self.get_profile(user_id)

        if dialect not in profile["learned_words"]:
            profile["learned_words"][dialect] = {
                "standard": standard,
                "learned_at": datetime.now().isoformat(),
                "context": context,
                "review_count": 0,
                "mastered": False,
            }
            profile["learning_history"].append(
                {
                    "word": dialect,
                    "action": "learn",
                    "timestamp": datetime.now().isoformat(),
                    "context": context,
                }
            )
        else:
            # 增加使用次数
            profile["learned_words"][dialect]["review_count"] += 1
            if profile["learned_words"][dialect]["review_count"] >= 3:
                profile["learned_words"][dialect]["mastered"] = True

        # 更新置信度
        profile["confidence"][dialect] = min(
            1.0, profile.get("confidence", {}).get(dialect, 0) + 0.2
        )

        self.save_profile(user_id, profile)
        return {
            "learned": True,
            "mastered": profile["learned_words"][dialect]["mastered"],
        }

    def translate(self, user_id: str, text: str) -> str:
        """根据用户画像翻译方言"""
        profile = self.get_profile(user_id)
        result = text

        # 按掌握程度排序（已掌握的优先）
        learned = profile.get("learned_words", {})
        sorted_words = sorted(
            learned.items(), key=lambda x: x[1].get("review_count", 0), reverse=True
        )

        for dialect, info in sorted_words:
            if dialect in result:
                result = result.replace(dialect, info["standard"])

        return result

    def get_stats(self, user_id: str) -> Dict:
        """获取用户学习统计"""
        profile = self.get_profile(user_id)
        learned = profile.get("learned_words", {})
        mastered = sum(1 for w in learned.values() if w.get("mastered", False))

        return {
            "user_id": user_id,
            "location": profile.get("location"),
            "dialect": profile.get("dialect"),
            "total_learned": len(learned),
            "mastered": mastered,
            "learning_progress": mastered / len(learned) if learned else 0,
        }


user_dialect = UserDialectProfile()
