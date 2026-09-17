#!/usr/bin/env python3
"""Skill Learner - Skill Learner 模块

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

"""技能学习器 - 从成功组合中自动生成新技能"""

import json
from datetime import datetime
from pathlib import Path


class SkillLearner:
    def __init__(self):
        self.combos_file = Path(f"{get_data_root()}/skill_stats/successful_combos.json")
        self.generated_file = Path(
            f"{get_data_root()}/skill_stats/generated_skills.json"
        )
        self._load()

    def _load(self):
        if self.combos_file.exists():
            with open(self.combos_file, "r") as f:
                self.combos = json.load(f)
        else:
            self.combos = {"combos": [], "stats": {}}

        if self.generated_file.exists():
            with open(self.generated_file, "r") as f:
                self.generated = json.load(f)
        else:
            self.generated = {"skills": []}

    def _save_combos(self):
        with open(self.combos_file, "w") as f:
            json.dump(self.combos, f, indent=2, default=str)

    def _save_generated(self):
        with open(self.generated_file, "w") as f:
            json.dump(self.generated, f, indent=2)

    def record_success(self, intent: str, skills: list, task: str = ""):
        combo_key = f"{intent}|{'|'.join(skills)}"

        if "stats" not in self.combos:
            self.combos["stats"] = {}

        if combo_key not in self.combos["stats"]:
            self.combos["stats"][combo_key] = 0
        self.combos["stats"][combo_key] += 1
        count = self.combos["stats"][combo_key]

        self._save_combos()
        print(f"📊 记录组合: {combo_key} (第{count}次)")

        if count >= 3:
            self._generate_skill(intent, skills, combo_key)

    def _generate_skill(self, intent: str, skills: list, combo_key: str):
        for existing in self.generated.get("skills", []):
            if existing.get("combo_key") == combo_key:
                print(f"⏭️ 技能已存在，跳过生成")
                return

        skill_name = f"auto_{intent.replace(' ', '_').lower()}"

        # 生成技能代码 - 修复 f-string 问题
        code = f'''"""
自动生成技能: {intent}
组合技能: {skills}
生成时间: {datetime.now().isoformat()}
"""

class {skill_name.title().replace('_', '')}Skill:
    def __init__(self):
        self.name = "{skill_name}"
        self.version = "1.0.0"
        self.composed_skills = {skills}
    
    def execute(self, params: dict) -> dict:
        from core.lib.skill_loader_v3 import skill_loader

        results = {{}}
        for skill in self.composed_skills:
            result = skill_loader.execute(skill, params)
            results[skill] = result

        return {{
            "success": all(r.get('success', False) for r in results.values()),
            "results": results,
            "message": f"执行{{len(self.composed_skills)}}个技能完成{self.name}"
        }}

skill = {skill_name.title().replace('_', '')}Skill()
'''

        skill_file = Path(f"skills/auto_generated/{skill_name}.py")
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text(code)

        import json

        registry_file = Path(f"{get_data_root()}/skill_registry_v2.json")
        if registry_file.exists():
            with open(registry_file, "r") as f:
                registry = json.load(f)
        else:
            registry = {}

        registry[skill_name] = {
            "name": skill_name,
            "category": "auto_generated",
            "category_name": "自动生成",
            "version": "1.0.0",
            "enabled": True,
            "created_at": datetime.now().isoformat(),
            "composed_skills": skills,
        }

        with open(registry_file, "w") as f:
            json.dump(registry, f, indent=2)

        self.generated["skills"].append(
            {
                "skill_name": skill_name,
                "intent": intent,
                "composed_skills": skills,
                "combo_key": combo_key,
                "created_at": datetime.now().isoformat(),
            }
        )
        self._save_generated()

        print(f"🎉 自动生成新技能: {skill_name}")
        print(f"   组合: {skills}")
        print(f"   意图: {intent}")


skill_learner = SkillLearner()

# 在 record_success 中，当 count == 3 时立即生成
# 当前逻辑已经正确，但可能因为某些原因没执行
# 确保生成函数被调用
