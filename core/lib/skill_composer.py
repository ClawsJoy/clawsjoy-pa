#!/usr/bin/env python3
"""Skill Composer - Skill Composer 模块

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

"""技能组合推荐引擎"""
import json
from collections import defaultdict
from pathlib import Path


class SkillComposer:
    def __init__(self):
        self.combos_file = Path(f"{get_data_root()}/skill_stats/successful_combos.json")
        self._load()

    def _load(self):
        if self.combos_file.exists():
            with open(self.combos_file, "r") as f:
                self.combos = json.load(f)
        else:
            self.combos = {"combos": []}

    def record_combo(self, skills: list, task: str, success: bool):
        if success:
            self.combos["combos"].append(
                {
                    "skills": skills,
                    "task": task,
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                }
            )
            self._save()

    def _save(self):
        self.combos_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.combos_file, "w") as f:
            json.dump(self.combos, f, indent=2)

    def recommend_combo(self, task: str) -> list:
        """根据任务推荐技能组合"""
        # 简单匹配：找相似任务的成功组合
        for combo in reversed(self.combos["combos"]):
            if combo["task"] == task or any(k in task for k in combo["task"].split()):
                return combo["skills"]
        return []


skill_composer = SkillComposer()
