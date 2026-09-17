#!/usr/bin/env python3
"""Skill Registry - Skill Registry 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import json
from datetime import datetime
from pathlib import Path

from core.lib.config_helper import get_data_root


class SkillRegistry:
    def __init__(self, record_file=f"{get_data_root()}/skill_generation_records.json"):
        self.record_file = Path(record_file)
        self.records = self._load()

    def _load(self):
        if self.record_file.exists():
            with open(self.record_file, "r") as f:
                return json.load(f)
        return {"generated": [], "reviewed": [], "rejected": []}

    def _save(self):
        with open(self.record_file, "w") as f:
            json.dump(self.records, f, indent=2, ensure_ascii=False)

    def add_record(self, requirement, skill_name, code_preview, status="pending"):
        """添加生成记录"""
        record = {
            "id": len(self.records["generated"]) + 1,
            "timestamp": datetime.now().isoformat(),
            "requirement": requirement,
            "skill_name": skill_name,
            "code_preview": code_preview[:500],
            "status": status,
            "review_comment": None,
        }
        self.records["generated"].append(record)
        self._save()
        return record["id"]

    def review(self, record_id, approved, comment=""):
        """人工复检"""
        for record in self.records["generated"]:
            if record["id"] == record_id:
                record["status"] = "approved" if approved else "rejected"
                record["review_comment"] = comment
                record["reviewed_at"] = datetime.now().isoformat()

                if approved:
                    self.records["reviewed"].append(record)
                else:
                    self.records["rejected"].append(record)
                break
        self._save()
        return True

    def get_pending(self):
        """获取待复检的记录"""
        return [r for r in self.records["generated"] if r["status"] == "pending"]

    def get_all(self):
        """获取所有生成的技能记录"""
        return self.records["generated"]

    def list_all(self):
        """列出所有技能 - 兼容接口"""
        return self.get_all()

    def list_skills(self):
        """列出所有技能名称 - 兼容接口"""
        return [r.get("skill_name") for r in self.get_all() if r.get("skill_name")]


skill_registry = SkillRegistry()
