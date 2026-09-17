#!/usr/bin/env python3
"""Skill Stats - Skill Stats 模块

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

"""技能执行统计 - 学习用户偏好"""
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class SkillStats:
    def __init__(self):
        self.stats_file = Path(f"{get_data_root()}/skill_stats/execution_stats.json")
        self._load()

    def _load(self):
        if self.stats_file.exists():
            with open(self.stats_file, "r") as f:
                self.stats = json.load(f)
        else:
            self.stats = {
                "total": 0,
                "success": 0,
                "failed": 0,
                "by_skill": {},
                "by_user": {},
            }

    def _save(self):
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.stats_file, "w") as f:
            json.dump(self.stats, f, indent=2)

    def record(self, user_id: str, skill_name: str, success: bool, duration: float):
        self.stats["total"] += 1
        if success:
            self.stats["success"] += 1
        else:
            self.stats["failed"] += 1

        if skill_name not in self.stats["by_skill"]:
            self.stats["by_skill"][skill_name] = {"total": 0, "success": 0}
        self.stats["by_skill"][skill_name]["total"] += 1
        if success:
            self.stats["by_skill"][skill_name]["success"] += 1

        if user_id not in self.stats["by_user"]:
            self.stats["by_user"][user_id] = {"skills": {}, "preferences": {}}

        self._save()

    def get_recommendations(self, user_id: str, task: str) -> list:
        """根据用户历史推荐技能"""
        user_stats = self.stats["by_user"].get(user_id, {})
        # 按成功率排序返回常用技能
        skills_used = user_stats.get("skills", {})
        sorted_skills = sorted(
            skills_used.items(), key=lambda x: -x[1].get("success", 0)
        )
        return [s[0] for s in sorted_skills[:5]]

    def get_top_skills(self, limit: int = 10) -> list:
        """获取最常用技能"""
        sorted_skills = sorted(
            self.stats["by_skill"].items(), key=lambda x: -x[1]["total"]
        )
        return [
            {
                "name": s[0],
                "total": s[1]["total"],
                "success_rate": (
                    s[1]["success"] / s[1]["total"] if s[1]["total"] > 0 else 0
                ),
            }
            for s in sorted_skills[:limit]
        ]


skill_stats = SkillStats()
