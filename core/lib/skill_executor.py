#!/usr/bin/env python3
"""Skill Executor - Skill Executor 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class SkillExecutor:
    def __init__(self):
        self._skill_loader = None

    @property
    def skill_loader(self):
        if self._skill_loader is None:
            from core.lib.skill_loader_v3 import skill_loader

            self._skill_loader = skill_loader
        return self._skill_loader

    def execute(self, skill_name: str, params: dict) -> dict:
        print(f"[DEBUG] 执行技能: {skill_name}", flush=True)

        # 获取技能信息
        skill_info = self.skill_loader.skills.get(skill_name)
        if not skill_info:
            print(f"[DEBUG] 技能不存在: {skill_name}", flush=True)
            return {"success": False, "error": f"技能不存在: {skill_name}"}

        print(f"[DEBUG] 找到技能: {skill_name}", flush=True)

        try:
            # 动态导入技能模块
            module_path = skill_info["path"]
            module = __import__(module_path, fromlist=["skill"])
            if hasattr(module, "skill") and hasattr(module.skill, "execute"):
                result = module.skill.execute(params)
                return {"success": True, "result": result, "skill": skill_name}
            else:
                return {"success": False, "error": f"技能 {skill_name} 格式不正确"}
        except Exception as e:
            print(f"[DEBUG] 执行失败: {e}", flush=True)
            return {"success": False, "error": str(e)}


skill_executor = SkillExecutor()
