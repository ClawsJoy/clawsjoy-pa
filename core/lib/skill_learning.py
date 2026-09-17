#!/usr/bin/env python3
"""Skill Learning - Skill Learning 模块

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

"""配置驱动的技能学习器"""

import json
from datetime import datetime
from pathlib import Path

import yaml


class SkillLearning:
    def __init__(self):
        self._load_config()
        self._load_data()

    def _load_config(self):
        config_file = Path("config/skill_learning.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                self.config = unified_config.get("skill_learning", {})
        else:
            self.config = {"learning": {"enabled": True, "min_success_count": 3}}

    def _load_data(self):
        combos_file = Path(f"{get_data_root()}/skill_stats/successful_combos.json")
        if combos_file.exists():
            with open(combos_file, "r") as f:
                self.combos = json.load(f)
        else:
            self.combos = {"stats": {}}

        generated_file = Path(f"{get_data_root()}/skill_stats/generated_skills.json")
        if generated_file.exists():
            with open(generated_file, "r") as f:
                self.generated = json.load(f)
        else:
            self.generated = {"skills": []}

    def _save_data(self):
        combos_file = Path(f"{get_data_root()}/skill_stats/successful_combos.json")
        with open(combos_file, "w") as f:
            json.dump(self.combos, f, indent=2)

        generated_file = Path(f"{get_data_root()}/skill_stats/generated_skills.json")
        with open(generated_file, "w") as f:
            json.dump(self.generated, f, indent=2)

    def record(self, intent: str, skills: list):
        """记录成功组合"""
        combo_key = f"{intent}|{'|'.join(skills)}"

        if combo_key not in self.combos.get("stats", {}):
            self.combos["stats"][combo_key] = 0
        self.combos["stats"][combo_key] += 1
        count = self.combos["stats"][combo_key]

        self._save_data()
        print(f"📊 记录: {combo_key} ({count}次)")

        # 检查是否需要生成
        min_count = self.config["learning"].get("min_success_count", 3)
        if count >= min_count:
            self._generate(intent, skills, combo_key)

    def _generate(self, intent: str, skills: list, combo_key: str):
        """生成新技能"""
        # 检查是否已生成
        for existing in self.generated.get("skills", []):
            if existing.get("combo_key") == combo_key:
                return

        skill_name = f"auto_{intent.replace(' ', '_').lower()}"

        # 创建技能文件
        output_dir = Path("skills/auto_generated")
        output_dir.mkdir(parents=True, exist_ok=True)

        code = f'''"""
自动生成: {intent}
组合: {skills}
"""

def execute(params):
    from core.lib.skill_loader_v3 import skill_loader
    results = {{}}
    for skill in {skills}:
        results[skill] = skill_loader.execute(skill, params)
    return {{"success": True, "results": results}}

skill = None
'''

        skill_file = output_dir / f"{skill_name}.py"
        skill_file.write_text(code)

        # 注册到技能注册中心
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
            "enabled": True,
            "created_at": datetime.now().isoformat(),
        }

        with open(registry_file, "w") as f:
            json.dump(registry, f, indent=2)

        self.generated["skills"].append(
            {
                "skill_name": skill_name,
                "intent": intent,
                "combo_key": combo_key,
                "created_at": datetime.now().isoformat(),
            }
        )
        self._save_data()

        print(f"🎉 自动生成新技能: {skill_name}")
        print(f"   文件: {skill_file}")
        print(f"   组合: {skills}")


skill_learning = SkillLearning()
