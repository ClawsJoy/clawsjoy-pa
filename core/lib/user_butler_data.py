#!/usr/bin/env python3
"""User Butler Data - User Butler Data 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class UserButlerData:
    """用户私人管家数据管理器"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.data_dir = Path(f"data/users/{user_id}/butler")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 初始化用户数据文件（如果不存在）
        self._init_user_files()

    def _init_user_files(self):
        """初始化用户数据文件"""
        template_dir = Path("data/users/template/butler")

        for template_file in template_dir.glob("*.yaml"):
            user_file = self.data_dir / template_file.name
            if not user_file.exists():
                with open(template_file, "r") as f:
                    content = f.read()
                with open(user_file, "w") as f:
                    f.write(content)

    # ========== 覆盖系统预设 ==========
    def get_override(self, key: str) -> Optional[Any]:
        """获取用户覆盖值"""
        overrides = self._load_yaml("overrides.yaml")
        return overrides.get(key)

    def set_override(self, key: str, value: Any):
        """设置用户覆盖（用户通过自然语言修改）"""
        overrides = self._load_yaml("overrides.yaml")
        overrides[key] = value
        self._save_yaml("overrides.yaml", overrides)

    def remove_override(self, key: str):
        """移除覆盖（恢复系统预设）"""
        overrides = self._load_yaml("overrides.yaml")
        if key in overrides:
            del overrides[key]
            self._save_yaml("overrides.yaml", overrides)

    # ========== 用户画像 ==========
    def get_profile(self, key: str = None):
        """获取用户画像"""
        profile = self._load_yaml("profile.yaml")
        if key:
            return profile.get(key)
        return profile

    def update_profile(self, updates: Dict):
        """更新用户画像"""
        profile = self._load_yaml("profile.yaml")
        profile.update(updates)
        profile["last_updated"] = datetime.now().isoformat()
        self._save_yaml("profile.yaml", profile)

    # ========== 学习偏好 ==========
    def learn_preference(self, key: str, value: Any, confidence: float = 0.5):
        """学习用户偏好（从交互中）"""
        learned = self._load_yaml("learned.yaml")

        if "preferences" not in learned:
            learned["preferences"] = {}

        old = learned["preferences"].get(key, {})
        new_confidence = min(1.0, old.get("confidence", 0) + confidence)

        learned["preferences"][key] = {
            "value": value,
            "confidence": new_confidence,
            "learned_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
        }
        learned["last_updated"] = datetime.now().isoformat()
        self._save_yaml("learned.yaml", learned)

    def get_preference(self, key: str, default=None) -> Optional[Any]:
        """获取学习到的偏好"""
        learned = self._load_yaml("learned.yaml")
        pref = learned.get("preferences", {}).get(key)
        if pref and pref.get("confidence", 0) > 0.3:
            # 更新最后使用时间
            pref["last_used"] = datetime.now().isoformat()
            self._save_yaml("learned.yaml", learned)
            return pref.get("value")
        return default

    def decay_preferences(self):
        """衰减偏好（长期不使用降低置信度）"""
        learned = self._load_yaml("learned.yaml")
        changed = False

        for key, pref in learned.get("preferences", {}).items():
            last_used = datetime.fromisoformat(pref.get("last_used", "2000-01-01"))
            days_since = (datetime.now() - last_used).days

            if days_since > 30:
                pref["confidence"] *= 0.8
                changed = True

            if pref.get("confidence", 0) < 0.2:
                del learned["preferences"][key]
                changed = True

        if changed:
            self._save_yaml("learned.yaml", learned)

    def forget(self, topic: str):
        """用户要求遗忘"""
        learned = self._load_yaml("learned.yaml")

        # 删除相关偏好
        for key in list(learned.get("preferences", {}).keys()):
            if topic.lower() in key.lower():
                del learned["preferences"][key]

        # 删除相关覆盖
        overrides = self._load_yaml("overrides.yaml")
        for key in list(overrides.keys()):
            if topic.lower() in key.lower():
                del overrides[key]

        self._save_yaml("learned.yaml", learned)
        self._save_yaml("overrides.yaml", overrides)

    # ========== 权重管理 ==========
    def get_weights(self) -> Dict:
        """获取三引擎权重"""
        weights = self._load_yaml("weights.yaml")
        return {
            "rule": weights.get("rule", 0.6),
            "memory": weights.get("memory", 0.3),
            "llm": weights.get("llm", 0.1),
        }

    def update_weight(self, engine: str, delta: float):
        """更新权重（命中时增加，未命中时减少）"""
        weights = self._load_yaml("weights.yaml")
        old = weights.get(engine, 0.5)
        new = max(0.05, min(0.85, old + delta))
        weights[engine] = new
        weights["last_updated"] = datetime.now().isoformat()

        # 归一化
        total = sum(weights.get(e, 0) for e in ["rule", "memory", "llm"])
        if total > 0:
            for e in ["rule", "memory", "llm"]:
                weights[e] = round(weights[e] / total, 3)

        self._save_yaml("weights.yaml", weights)

    # ========== 有效配置获取 ==========
    def get_effective_config(self, key: str, system_default: Any) -> Any:
        """获取有效配置：用户覆盖 > 学习偏好 > 系统默认"""

        # 1. 用户覆盖（权重最高）
        override = self.get_override(key)
        if override is not None:
            return override, 0.9

        # 2. 学习偏好（权重中等）
        learned = self.get_preference(key)
        if learned is not None:
            return learned, 0.7

        # 3. 系统默认（权重最低）
        return system_default, 0.3

    # ========== 私有方法 ==========
    def _load_yaml(self, filename: str) -> Dict:
        filepath = self.data_dir / filename
        if filepath.exists():
            with open(filepath, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _save_yaml(self, filename: str, data: Dict):
        filepath = self.data_dir / filename
        with open(filepath, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
