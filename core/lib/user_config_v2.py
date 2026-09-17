#!/usr/bin/env python3
"""User Config V2 - User Config V2 模块

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

"""用户配置 v2 - 分层设计：系统基础(只读) + 用户自定义(可修改) + 私有记忆(不可复制)"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class UserConfigV2:
    """
    配置分层:
    1. system_base: 系统基础能力（只读，锁死）
    2. user_custom: 用户自定义（可修改，可重置）
    3. user_private: 用户私有记忆（不可复制，不可导出）
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.user_dir = Path(
            funified_config.get("paths.users_dir", f"{get_data_root()}/users/")
            + "/{user_id}"
        )
        self.user_dir.mkdir(parents=True, exist_ok=True)

        # 三个配置文件
        self.system_base_file = Path("config/user_system_base.yaml")  # 系统级，只读
        self.user_custom_file = self.user_dir / "custom.yaml"  # 用户自定义，可修改
        self.user_private_file = self.user_dir / "private.yaml"  # 用户私有，不可复制

        self._load()

    def _load(self):
        """加载三层配置"""
        # 1. 系统基础（只读，从系统配置加载）
        if self.system_base_file.exists():
            with open(self.system_base_file, "r") as f:
                self.system_base = unified_config.get("user_v2", {}) or {}
        else:
            self.system_base = self._get_system_base()

        # 2. 用户自定义（可修改）
        if self.user_custom_file.exists():
            with open(self.user_custom_file, "r") as f:
                self.user_custom = unified_config.get("user_v2", {}) or {}
        else:
            self.user_custom = self._get_default_custom()
            self._save_custom()

        # 3. 用户私有（不可复制，不可导出）
        if self.user_private_file.exists():
            with open(self.user_private_file, "r") as f:
                self.user_private = unified_config.get("user_v2", {}) or {}
        else:
            self.user_private = self._get_default_private()
            self._save_private()

    def _get_system_base(self) -> Dict:
        """系统基础能力（只读，所有用户共享）"""
        return {
            "version": "4.0.0",
            "system_skills": {
                "language_master": {
                    "base_config": {"translation_style": "concise", "auto_learn": True},
                    "readonly": True,
                    "description": "系统级翻译能力，不可修改",
                },
                "video_maker": {
                    "base_config": {"output_format": "mp4", "resolution": "1920x1080"},
                    "readonly": True,
                },
            },
            "system_agents": {
                "personal_butler": {
                    "base_config": {
                        "greeting_style": "warm",
                        "memory_retention_days": 30,
                    },
                    "readonly": True,
                }
            },
            "security": {"max_custom_vocab": 100, "max_installed_skills": 50},
        }

    def _get_default_custom(self) -> Dict:
        """用户自定义默认配置（可修改）"""
        return {
            "user_profile": {
                "name": self.user_id,
                "preference": "default",
                "theme": "dark",
                "language": "zh-CN",
            },
            "installed_skills": {},
            "installed_agents": {},
            "custom_vocab": {},
            "skill_overrides": {},
            "created_at": datetime.now().isoformat(),
        }

    def _get_default_private(self) -> Dict:
        """用户私有记忆（不可复制）"""
        return {
            "memory": [],
            "learning_history": [],
            "user_habits": {},
            "conversation_history": [],
            "private_notes": {},
            "created_at": datetime.now().isoformat(),
        }

    def _save_custom(self):
        """保存用户自定义配置"""
        with open(self.user_custom_file, "w") as f:
            yaml.dump(self.user_custom, f, allow_unicode=True, default_flow_style=False)

    def _save_private(self):
        """保存用户私有记忆"""
        with open(self.user_private_file, "w") as f:
            yaml.dump(
                self.user_private, f, allow_unicode=True, default_flow_style=False
            )

    # ========== 系统基础（只读） ==========
    def get_system_base(self, path: str = None) -> Any:
        """获取系统基础配置（只读）"""
        if path:
            keys = path.split(".")
            value = self.system_base
            for k in keys:
                value = value.get(k) if isinstance(value, dict) else None
                if value is None:
                    return None
            return value
        return self.system_base

    # ========== 用户自定义（可修改） ==========
    def get_custom(self, path: str = None) -> Any:
        """获取用户自定义配置"""
        if path:
            keys = path.split(".")
            value = self.user_custom
            for k in keys:
                value = value.get(k) if isinstance(value, dict) else None
                if value is None:
                    return None
            return value
        return self.user_custom

    def set_custom(self, path: str, value: Any):
        """设置用户自定义配置"""
        keys = path.split(".")
        target = self.user_custom
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value
        self._save_custom()

    def reset_custom(self):
        """重置用户自定义配置（恢复默认）"""
        self.user_custom = self._get_default_custom()
        self._save_custom()
        return {"success": True, "message": "自定义配置已重置"}

    def install_skill(self, skill_name: str, custom_config: Dict = None):
        """安装技能（用户自定义部分）"""
        if "installed_skills" not in self.user_custom:
            self.user_custom["installed_skills"] = {}

        self.user_custom["installed_skills"][skill_name] = {
            "enabled": True,
            "custom_config": custom_config or {},
            "installed_at": datetime.now().isoformat(),
        }
        self._save_custom()

    def uninstall_skill(self, skill_name: str):
        """卸载技能"""
        if skill_name in self.user_custom.get("installed_skills", {}):
            del self.user_custom["installed_skills"][skill_name]
            self._save_custom()

    # ========== 用户私有（不可复制） ==========
    def get_private(self, path: str = None) -> Any:
        """获取私有记忆"""
        if path:
            keys = path.split(".")
            value = self.user_private
            for k in keys:
                value = value.get(k) if isinstance(value, dict) else None
                if value is None:
                    return None
            return value
        return self.user_private

    def add_private_memory(self, content: str, memory_type: str = "general"):
        """添加私有记忆（不可复制）"""
        if "memory" not in self.user_private:
            self.user_private["memory"] = []

        self.user_private["memory"].append(
            {
                "content": content,
                "type": memory_type,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self._save_private()

    def add_learning_history(self, query: str, result: str, success: bool):
        """记录学习历史"""
        if "learning_history" not in self.user_private:
            self.user_private["learning_history"] = []

        self.user_private["learning_history"].append(
            {
                "query": query,
                "result": result,
                "success": success,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self._save_private()

    def clear_private_memory(self):
        """清除私有记忆（用户主动清除）"""
        self.user_private = self._get_default_private()
        self._save_private()
        return {"success": True, "message": "私有记忆已清除"}

    def export_custom(self) -> Dict:
        """导出用户自定义配置（可用于迁移）"""
        return {
            "user_id": self.user_id,
            "custom_config": self.user_custom,
            "exported_at": datetime.now().isoformat(),
        }

    def import_custom(self, export_data: Dict):
        """导入用户自定义配置（恢复）"""
        if export_data.get("user_id") == self.user_id:
            self.user_custom = export_data.get("custom_config", self.user_custom)
            self._save_custom()
            return {"success": True, "message": "配置已恢复"}
        return {"success": False, "error": "用户ID不匹配"}

    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "system_base_version": self.system_base.get("version"),
            "custom_skills": len(self.user_custom.get("installed_skills", {})),
            "private_memories": len(self.user_private.get("memory", [])),
            "learning_history": len(self.user_private.get("learning_history", [])),
        }


def get_user_config_v2(user_id: str) -> UserConfigV2:
    return UserConfigV2(user_id)


# DEPRECATED: 请使用 unified_config 代替
