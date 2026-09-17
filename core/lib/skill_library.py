#!/usr/bin/env python3
"""Skill Library - Skill Library 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""技能库加载器 - 加载符合规范的技能清单"""
import json
from pathlib import Path
from typing import Dict, List, Optional


class SkillLibrary:
    def __init__(self, manifests_dir="manifests"):
        self.manifests_dir = Path(manifests_dir)
        self.atomic_skills: Dict = {}
        self.workflow_skills: Dict = {}
        self._load_all()

    def _load_all(self):
        # 加载原子技能
        atomic_dir = self.manifests_dir / "atomic"
        if atomic_dir.exists():
            for f in atomic_dir.glob("*.json"):
                with open(f, "r") as fp:
                    manifest = json.load(fp)
                    self.atomic_skills[manifest["name"]] = manifest
                    print(f"✅ 加载原子技能: {manifest['name']}")

        # 加载工作流技能
        workflow_dir = self.manifests_dir / "workflow"
        if workflow_dir.exists():
            for f in workflow_dir.glob("*.json"):
                with open(f, "r") as fp:
                    manifest = json.load(fp)
                    self.workflow_skills[manifest["name"]] = manifest
                    print(f"✅ 加载工作流: {manifest['name']}")

    def get_atomic(self, name: str) -> Optional[Dict]:
        return self.atomic_skills.get(name)

    def get_workflow(self, name: str) -> Optional[Dict]:
        return self.workflow_skills.get(name)

    def list_atomic(self) -> List[str]:
        return list(self.atomic_skills.keys())

    def list_workflows(self) -> List[str]:
        return list(self.workflow_skills.keys())

    def get_best_workflow(self, goal: str) -> Optional[Dict]:
        """根据目标推荐最佳工作流"""
        goal_lower = goal.lower()
        for name, wf in self.workflow_skills.items():
            for tag in wf.get("tags", []):
                if tag in goal_lower:
                    return wf
        return None


skill_library = SkillLibrary()
