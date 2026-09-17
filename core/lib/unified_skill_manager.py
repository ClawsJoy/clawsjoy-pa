#!/usr/bin/env python3
"""Unified Skill Manager - Unified Skill Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from typing import Dict, List, Optional

from core.lib.skill_loader_v3 import get_skill_loader

skill_loader = get_skill_loader()
from core.lib.skill_registry_v2 import skill_registry


class UnifiedSkillManager:
    """统一技能管理器 - 单例模式"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._sync()
        print("✅ 统一技能管理器已初始化")

    def _sync(self):
        """同步两个技能注册表"""
        # 获取所有技能
        loader_skills = set(skill_loader.list_skills())
        registry_skills = set(skill_registry.list_all())

        # 将 loader 中缺失的技能注册到 registry
        missing_in_registry = loader_skills - registry_skills
        for skill_name in missing_in_registry:
            # 获取技能信息
            skill_info = skill_loader.skills.get(skill_name, {})
            category = skill_info.get("category", "general")
            skill_registry.register(skill_name, category, "1.0.0")

        # 将 registry 中缺失的技能添加到 loader（如果文件存在）
        missing_in_loader = registry_skills - loader_skills
        for skill_name in missing_in_loader:
            # 检查技能文件是否存在
            import os
            from pathlib import Path

            for cat_dir in skill_loader.categories.keys():
                skill_path = Path(f"skills/{cat_dir}/{skill_name}.py")
                if skill_path.exists():
                    skill_loader.skills[skill_name] = {
                        "name": skill_name,
                        "category": cat_dir,
                        "category_name": skill_loader.categories.get(cat_dir, cat_dir),
                        "file": str(skill_path),
                        "path": f"skills.{cat_dir}.{skill_name}",
                    }
                    break

        # 同步后统计
        self._all_skills = list(loader_skills | registry_skills)
        print(f"   统一后技能总数: {len(self._all_skills)}")

    def list_all(self) -> List[str]:
        """获取所有技能列表"""
        return self._all_skills

    def get_skill(self, name: str):
        """获取技能（优先从 loader 获取）"""
        skill = skill_loader.get_skill(name)
        if skill:
            return skill
        # 尝试从 registry 获取
        return skill_registry.get(name)

    def execute(self, name: str, params: dict) -> dict:
        """执行技能"""
        skill = self.get_skill(name)
        if skill and hasattr(skill, "execute"):
            return skill.execute(params)
        return {"success": False, "error": f"技能不存在: {name}"}

    def reload(self):
        """热重载所有技能"""
        self._sync()
        return {"success": True, "total": len(self._all_skills)}


unified_manager = UnifiedSkillManager()
