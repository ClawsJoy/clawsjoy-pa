"""用户画像管理 - 语言能力、偏好"""

import json
from pathlib import Path
from typing import Dict, List, Optional


class UserProfile:
    """用户画像管理器"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._profile = self._load_profile()
    
    def _get_path(self) -> Path:
        return Path(f"data/profile/{self.user_id}.json")
    
    def _load_profile(self) -> Dict:
        path = self._get_path()
        if path.exists():
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "user_id": self.user_id,
            "languages": {
                "native": "普通话",
                "fluent": [],
                "learning": []
            },
            "dialects": {},
            "preferences": {}
        }
    
    def _save(self):
        path = self._get_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self._profile, f, indent=2, ensure_ascii=False)
    
    def set_native_language(self, language: str):
        """设置母语"""
        self._profile["languages"]["native"] = language
        self._save()
    
    def add_dialect(self, name: str, words: Dict = None):
        """添加方言能力"""
        self._profile["dialects"][name] = {
            "level": "native" if name == self._profile["languages"]["native"] else "conversational",
            "words": words or {}
        }
        self._save()
    
    def get_preferred_language(self) -> str:
        """获取偏好语言"""
        return self._profile.get("preferences", {}).get("language", self._profile["languages"]["native"])
    
    def to_dict(self) -> Dict:
        return self._profile


# 全局实例缓存
_profile_cache = {}

def get_user_profile(user_id: str) -> UserProfile:
    if user_id not in _profile_cache:
        _profile_cache[user_id] = UserProfile(user_id)
    return _profile_cache[user_id]
