from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""Skill Auto Trigger - Skill Auto Trigger 模块

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

"""
技能自动生成触发器
基于 skill_learning.yaml 配置，在任务成功后自动生成组合技能
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml


class SkillAutoTrigger:
    """技能自动生成触发器"""

    def __init__(self):
        self.config = self._load_config()
        self.combos_file = Path(f"{get_data_root()}/skill_stats/successful_combos.json")
        self.generated_file = Path(
            f"{get_data_root()}/skill_stats/generated_skills.json"
        )
        self.auto_gen_dir = Path("skills/auto_generated")
        self.auto_gen_dir.mkdir(parents=True, exist_ok=True)

        self._load_data()

    def _load_config(self) -> Dict:
        """从统一配置加载"""
        return unified_config.get(
            "skill_auto_trigger",
            {"learning": {"min_success_count": 3, "auto_generate": True}},
        )

    def _load_data(self):
        """加载统计数据"""
        if self.combos_file.exists():
            with open(self.combos_file, "r") as f:
                self.successful_combos = json.load(f)
        else:
            self.successful_combos = {}

        if self.generated_file.exists():
            with open(self.generated_file, "r") as f:
                self.generated_skills = json.load(f)
        else:
            self.generated_skills = {}

    def _save_data(self):
        """保存统计数据"""
        with open(self.combos_file, "w") as f:
            json.dump(self.successful_combos, f, indent=2)
        with open(self.generated_file, "w") as f:
            json.dump(self.generated_skills, f, indent=2)

    def record_success_combination(
        self, intent: str, skills: List[str], params: Dict = None
    ):
        """记录成功的技能组合"""
        combo_key = f"{intent}_{'_'.join(skills)}"

        if combo_key not in self.successful_combos:
            self.successful_combos[combo_key] = {
                "intent": intent,
                "skills": skills,
                "success_count": 0,
                "first_success": datetime.now().isoformat(),
                "last_success": None,
                "params": params or {},
            }

        self.successful_combos[combo_key]["success_count"] += 1
        self.successful_combos[combo_key]["last_success"] = datetime.now().isoformat()

        self._save_data()

        # 检查是否需要自动生成技能
        min_count = self.config.get("learning", {}).get("min_success_count", 3)
        auto_generate = self.config.get("learning", {}).get("auto_generate", True)

        if (
            auto_generate
            and self.successful_combos[combo_key]["success_count"] >= min_count
        ):
            if combo_key not in self.generated_skills:
                self._generate_skill(intent, skills)

        return combo_key

    def _generate_skill(self, intent: str, skills: List[str]):
        """生成组合技能"""
        skill_name = self._generate_skill_name(intent)
        skill_file = self.auto_gen_dir / f"auto_{skill_name}.py"

        if skill_file.exists():
            return

        # 使用配置中的模板
        template = self.config.get("generation", {}).get("skill_template", "")

        code = f'''"""
自动生成技能: {intent}
原始意图: {intent}
组合技能: {", ".join(skills)}
生成时间: {datetime.now().isoformat()}
"""

class Auto{skill_name.title()}Skill:
    def __init__(self):
        self.name = "auto_{skill_name}"
        self.composed_skills = {skills}
    
    def execute(self, params):
        from core.lib.skill_loader_v3 import skill_loader
        results = {{}}
        for skill in self.composed_skills:
            results[skill] = skill_loader.execute(skill, params)
        return {{
            "success": all(r.get('success', False) for r in results.values()),
            "results": results,
            "auto_generated": True,
            "intent": "{intent}"
        }}

skill = Auto{skill_name.title()}Skill()
'''

        with open(skill_file, "w") as f:
            f.write(code)

        # 记录已生成
        self.generated_skills[f"auto_{skill_name}"] = {
            "intent": intent,
            "skills": skills,
            "file": str(skill_file),
            "created_at": datetime.now().isoformat(),
        }
        self._save_data()

        print(f"✅ 自动生成技能: auto_{skill_name}")

        # 触发技能重载
        self._reload_skills()

    def _generate_skill_name(self, intent: str) -> str:
        """从意图生成技能名称"""
        import re

        # 移除常见词汇
        stop_words = ["帮我", "请", "一下", "一个", "的", "了", "和", "制作", "生成"]
        name = intent
        for word in stop_words:
            name = name.replace(word, "")
        name = re.sub(r"[^\u4e00-\u9fa5a-zA-Z]", "_", name)
        name = name[:30].strip("_")
        if not name:
            name = f"task_{int(datetime.now().timestamp())}"
        return name

    def _reload_skills(self):
        """触发技能重载"""
        try:
            import requests

            requests.post(
                f"http://{unified_config.get("services.gateway.host", "localhost")}:{unified_config.get("services.gateway.port", 5002)}/api/skills/reload",
                timeout=2,
            )
        except Exception as e:
            pass

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_combos": len(self.successful_combos),
            "generated_skills": len(self.generated_skills),
            "min_success_count": self.config.get("learning", {}).get(
                "min_success_count", 3
            ),
            "auto_generate_enabled": self.config.get("learning", {}).get(
                "auto_generate", True
            ),
        }


# 全局实例
_auto_trigger = None


def get_auto_trigger():
    global _auto_trigger
    if _auto_trigger is None:
        _auto_trigger = SkillAutoTrigger()
    return _auto_trigger
