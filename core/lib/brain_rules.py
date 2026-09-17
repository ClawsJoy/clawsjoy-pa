#!/usr/bin/env python3
"""Brain Rules - Brain Rules 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""大脑规则配置加载器"""
from pathlib import Path

import yaml


class BrainRules:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        config_file = Path(__file__).parent.parent / "config/brain_rules.yaml"
        if config_file.exists():
            with open(config_file, "r") as f:
                self._config = unified_config.get("brain_rules")
        else:
            self._config = self._default()

    def _default(self):
        return {
            "math": {"enabled": True, "pattern": r"(\d+)\s*([+\-*/])\s*(\d+)"},
            "memory_triggers": [],
            "report_triggers": [],
            "auto_fix_triggers": {},
        }

    def get_memory_query_stopwords(self):
        return self._config.get("memory_query", {}).get(
            "stopwords",
            [
                "查询",
                "搜索",
                "帮我",
                "查一下",
                "看看",
                "请问",
                "系统",
                "什么",
                "是",
                "多少",
            ],
        )

    def get_memory_query_fallback(self):
        return self._config.get("memory_query", {}).get("fallback", {})

    def get_memory_query_default(self):
        return self._config.get("memory_query", {}).get("default_query", "系统")

    def get_memory_query_default_n(self):
        return self._config.get("memory_query", {}).get("default_n", 10)

    def get_planning_max_skills(self):
        """获取规划最大技能数"""
        return self._config.get("planning", {}).get("max_skills", 20)

    def get_math_enabled(self):
        return self._config.get("math", {}).get("enabled", True)

    def get_math_pattern(self):
        return self._config.get("math", {}).get("pattern", r"(\d+)\s*([+\-*/])\s*(\d+)")

    def get_math_operators(self):
        return self._config.get("math", {}).get("operators", {})

    def get_memory_triggers(self):
        return self._config.get("memory_triggers", [])

    def get_report_triggers(self):
        return self._config.get("report_triggers", [])

    def is_memory_query(self, goal):
        return any(kw in goal for kw in self.get_memory_triggers())

    def is_report_generation(self, goal):
        return any(kw in goal for kw in self.get_report_triggers())

    def match_auto_fix(self, goal):
        goal_lower = goal.lower()
        triggers = self._config.get("auto_fix_triggers", {})

        check_config = triggers.get("service_check", {})
        if any(kw in goal_lower for kw in check_config.get("keywords", [])):
            for key, skill_name in check_config.get("skills", {}).items():
                if key in goal_lower:
                    return skill_name, {"action": "check"}

        fix_config = triggers.get("fix", {})
        if any(kw in goal_lower for kw in fix_config.get("keywords", [])):
            for key, skill_name in fix_config.get("skills", {}).items():
                if key in goal_lower:
                    return skill_name, {"action": "fix"}

        return None, None

    def get_llm_config(self):
        return self._config.get("llm_plan", {})

    def get_max_skills(self):
        return self.get_llm_config().get("max_skills", 20)

    def get_llm_fallback_to_direct(self):
        return self.get_llm_config().get("fallback_to_direct", True)


brain_rules = BrainRules()

__version__ = "1.0.0"
__version_date__ = "2026-05-19"
__version_author__ = "ClawsJoy"
__changelog__ = "从 config/brain_rules.yaml 读取大脑规则"
