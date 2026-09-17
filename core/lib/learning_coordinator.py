#!/usr/bin/env python3
"""Learning Coordinator - Learning Coordinator 模块

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

"""学习协调器 - 统一 RealLearner、SkillEvolver、LearningHooks"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

from core.lib.learning_hooks import LearningHooks
from core.lib.real_learner import RealLearner
from core.lib.skill_evolver import SkillEvolver
from core.lib.unified_config import unified_config


class LearningCoordinator:
    """学习协调器 - 配置驱动，自动注册"""

    def __init__(self):
        self._load_config()
        self.real_learner = RealLearner()
        self.skill_evolver = SkillEvolver()
        self.learning_hooks = LearningHooks()
        print("✅ 学习协调器已启动")

    def _load_config(self):
        config_file = Path("config/learning.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                self.config = unified_config.get("learning_coordinator", {})
        else:
            self.config = {}

    def process_feedback(self, context: Dict) -> Dict:
        """处理反馈，触发学习循环"""
        # 1. 记录交互
        self.learning_hooks.log_interaction(context)

        # 2. 记录真实数据
        self.real_learner.record_request(
            user_input=context.get("user_input", ""),
            task=context.get("task", ""),
            response_time=context.get("duration", 0),
            success=context.get("success", False),
        )

        # 3. 如果成功，尝试学习新模式
        patterns = []
        if context.get("success"):
            patterns = self._discover_patterns(context.get("code", ""))
            if patterns:
                self._auto_register_skills(patterns)

        return {"learned": True, "patterns": patterns}

    def _discover_patterns(self, code: str) -> List[str]:
        """发现代码模式"""
        discovered = []
        patterns_config = self.config.get("pattern_discovery", {}).get("patterns", [])

        for pattern in patterns_config:
            if re.search(pattern.get("regex", ""), code, re.IGNORECASE | re.DOTALL):
                discovered.append(pattern.get("skill"))

        return discovered

    def _auto_register_skills(self, skills: List[str]):
        """自动注册新技能"""
        registry_file = Path(f"{get_data_root()}/skill_registry_v2.json")

        if registry_file.exists():
            with open(registry_file, "r") as f:
                registry = json.load(f)
        else:
            registry = {}

        for skill_name in skills:
            if skill_name not in registry:
                registry[skill_name] = {
                    "name": skill_name,
                    "category": "auto_generated",
                    "version": "1.0.0",
                    "enabled": True,
                    "auto_registered": True,
                    "registered_at": datetime.now().isoformat(),
                }
                print(f"📚 自动注册新技能: {skill_name}")

        with open(registry_file, "w") as f:
            json.dump(registry, f, indent=2)


learning_coordinator = LearningCoordinator()
