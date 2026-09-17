#!/usr/bin/env python3
"""Skill Composer V4 - Skill Composer V4 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""技能组合指引器 v4.0.0 - 为 LLM 提供组合指引"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class SkillCapability:
    """技能能力描述"""

    name: str
    description: str
    use_when: List[str] = field(default_factory=list)
    not_for: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    output_format: str = ""
    security_grade: str = "A"


class SkillComposer:
    """技能组合指引器 - 为 LLM 提供组合指引"""

    VERSION = "4.0.0"

    def __init__(self, skills_path: Path = None):
        self.skills_path = skills_path or Path("skills")
        self.skills: Dict[str, SkillCapability] = {}
        self._load_all_skills()

    def _load_all_skills(self):
        """加载所有技能的能力描述"""
        for skill_dir in self.skills_path.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith("__"):
                continue

            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                try:
                    content = skill_md.read_text(encoding="utf-8")
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 2:
                            metadata = unified_config.get("skill_metadata", {})

                            use_when = metadata.get("use_when", "")
                            not_for = metadata.get("not_for", "")

                            self.skills[skill_dir.name] = SkillCapability(
                                name=skill_dir.name,
                                description=metadata.get("description", "")[:200],
                                use_when=(
                                    [
                                        u.strip()
                                        for u in use_when.split("\n")
                                        if u.strip()
                                    ]
                                    if use_when
                                    else []
                                ),
                                not_for=(
                                    [
                                        n.strip()
                                        for n in not_for.split("\n")
                                        if n.strip()
                                    ]
                                    if not_for
                                    else []
                                ),
                                dependencies=metadata.get("dependencies", []),
                                security_grade=metadata.get("security_grade", "A"),
                            )
                except Exception as e:
                    logger.warning(f"Failed to load {skill_dir.name}: {e}")

    def get_skill_guide(self) -> str:
        """获取技能指引（供 LLM 理解）"""
        guide = []
        guide.append("# Available Skills for Composition")
        guide.append("")

        for skill in self.skills.values():
            guide.append(f"## {skill.name}")
            guide.append(f"Description: {skill.description}")
            if skill.use_when:
                guide.append(f"Use when: {', '.join(skill.use_when[:3])}")
            if skill.not_for:
                guide.append(f"NOT for: {', '.join(skill.not_for[:3])}")
            if skill.dependencies:
                guide.append(f"Depends on: {', '.join(skill.dependencies)}")
            guide.append(
                f"Security: {'🟢' if skill.security_grade == 'A' else '🟡' if skill.security_grade == 'B' else '🟠'}"
            )
            guide.append("")

        return "\n".join(guide)

    def find_skills_for_intent(self, intent: str) -> List[str]:
        """根据意图匹配技能"""
        matched = []
        intent_lower = intent.lower()

        for name, skill in self.skills.items():
            for condition in skill.use_when:
                if condition.lower() in intent_lower:
                    matched.append(name)
                    break
            else:
                if any(word in intent_lower for word in name.lower().split("_")):
                    if name not in matched:
                        matched.append(name)

        return matched[:10]

    def compose_workflow(self, intent: str, selected_skills: List[str]) -> Dict:
        """生成工作流组合建议"""
        workflow = {"intent": intent, "steps": [], "estimated_success_rate": 0.8}

        for i, skill_name in enumerate(selected_skills):
            skill = self.skills.get(skill_name)
            step = {
                "order": i + 1,
                "skill": skill_name,
                "description": skill.description if skill else "Unknown",
                "depends_on": skill.dependencies if skill else [],
            }
            workflow["steps"].append(step)

        return workflow

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "version": self.VERSION,
            "total_skills": len(self.skills),
            "skills": list(self.skills.keys())[:10],
        }


composer = SkillComposer()


if __name__ == "__main__":
    print(f"技能组合指引器 v{composer.VERSION}")
    print(f"已加载 {len(composer.skills)} 个技能")

    intent = "生成一张图片并发布到视频平台"
    matched = composer.find_skills_for_intent(intent)
    print(f"\n意图: {intent}")
    print(f"匹配技能: {matched}")
