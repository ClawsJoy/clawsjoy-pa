#!/usr/bin/env python3
"""Skill Registry V2 - Skill Registry V2 模块

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

"""技能注册中心 V2 - 简化版"""
import json
from datetime import datetime
from pathlib import Path


class SkillRegistryV2:
    def __init__(self, registry_file=f"{get_data_root()}/skill_registry_v2.json"):
        self.registry_file = Path(registry_file)
        self.skills = {}
        self._load()

    def _load(self):
        if self.registry_file.exists():
            with open(self.registry_file, "r") as f:
                self.skills = json.load(f)

    def _save(self):
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_file, "w") as f:
            json.dump(self.skills, f, indent=2)

    def register(self, name, category, version="1.0.0"):
        self.skills[name] = {
            "name": name,
            "category": category,
            "version": version,
            "enabled": True,
            "created_at": datetime.now().isoformat(),
        }
        self._save()

    def get(self, name):
        return self.skills.get(name)

    def list_all(self):
        return list(self.skills.keys())

    def list_by_category(self, category):
        return [n for n, s in self.skills.items() if s.get("category") == category]

    def enable(self, name):
        if name in self.skills:
            self.skills[name]["enabled"] = True
            self._save()
            return True
        return False

    def disable(self, name):
        if name in self.skills:
            self.skills[name]["enabled"] = False
            self._save()
            return True
        return False

    def reload(self, name):
        return True

    def get_stats(self):
        categories = {}
        for s in self.skills.values():
            cat = s.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        return {"total": len(self.skills), "by_category": categories}


skill_registry = SkillRegistryV2()

# 注册已有技能
categories = {
    "add": "math",
    "multiply": "math",
    "divide": "math",
    "math_enhanced": "math",
    "remove_bg": "image",
    "spider": "image",
    "image_slideshow": "image",
    "manju_maker": "video",
    "video_uploader": "video",
    "add_subtitles": "video",
    "do_anything": "core",
    "calibrated_executor": "core",
    "quality_gate": "core",
}
for name, cat in categories.items():
    skill_registry.register(name, cat)

    def list_all(self):
        """兼容接口 - 返回所有技能列表"""
        return (
            self.list_all() if hasattr(self, "list_all") else list(self.registry.keys())
        )

    def get_all(self):
        """获取所有技能"""
        return self.list_all()

    def list_all(self):
        """
        列出所有技能（兼容接口）
        返回所有技能的名称列表
        """
        return list(self.registry.keys())

    def get_all_skills(self):
        """
        获取所有技能的详细信息
        返回技能名称和元数据的字典
        """
        return self.registry.copy()
