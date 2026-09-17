#!/usr/bin/env python3
"""Skill Adapter - Skill Adapter 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from core.lib.skill_loader_v3 import skill_loader as _original_loader


class UnifiedSkillInterface:
    """统一技能接口 - 包装原有 loader，提供兼容方法"""

    def __init__(self):
        self._loader = _original_loader

    def __getattr__(self, name):
        """代理所有方法到原始 loader"""
        return getattr(self._loader, name)

    def list_all(self):
        """兼容接口 - 映射到 list_skills"""
        if hasattr(self._loader, "list_skills"):
            return self._loader.list_skills()
        if hasattr(self._loader, "list_all"):
            return self._loader.list_all()
        return []

    def get_all(self):
        """兼容接口"""
        return self.list_all()


# 保持原有变量名，让现有代码继续工作
skill_loader = UnifiedSkillInterface()
unified_skill_interface = skill_loader
