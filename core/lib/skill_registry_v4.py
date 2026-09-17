#!/usr/bin/env python3
"""Skill Registry V4 - Skill Registry V4 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""OpenClaw 兼容技能注册中心 v4.0.0 - 修复版"""

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
class SkillMetadata:
    """技能元数据"""

    name: str
    version: str
    description: str
    use_when: str = ""
    not_for: str = ""
    author: str = "ClawsJoy"
    security_grade: str = "🟢 A"
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    path: str = ""


class SkillRegistry:
    """技能注册中心 - 直接扫描目录"""

    VERSION = "4.0.0"

    def __init__(self, skills_path: Optional[Path] = None):
        self.skills_path = skills_path or Path("skills")
        self.skills: Dict[str, SkillMetadata] = {}
        self._discover_skills()

    def _discover_skills(self):
        """直接扫描技能目录"""
        logger.info(f"扫描技能目录: {self.skills_path}")

        for skill_dir in self.skills_path.iterdir():
            if not skill_dir.is_dir():
                continue
            if skill_dir.name.startswith("__"):
                continue

            skill_name = skill_dir.name
            skill_md = skill_dir / "SKILL.md"
            main_py = skill_dir / "scripts" / "main.py"

            # 检查是否有 main.py（可执行技能）
            if not main_py.exists():
                logger.debug(f"跳过 {skill_name}: 缺少 main.py")
                continue

            # 解析元数据
            description = f"{skill_name} skill"
            use_when = ""
            not_for = ""
            version = "1.0.0"

            if skill_md.exists():
                try:
                    content = skill_md.read_text(encoding="utf-8")
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 2:
                            import yaml

                            metadata = unified_config.get("skill_metadata", {})
                            description = metadata.get("description", description)
                            use_when = metadata.get("use_when", "")
                            not_for = metadata.get("not_for", "")
                            version = metadata.get("version", version)
                except Exception as e:
                    logger.warning(f"解析 {skill_name} SKILL.md 失败: {e}")

            self.skills[skill_name] = SkillMetadata(
                name=skill_name,
                version=version,
                description=description[:200],
                use_when=use_when,
                not_for=not_for,
                enabled=True,
                path=str(skill_dir),
            )
            logger.info(f"✅ 注册技能: {skill_name} v{version}")

        logger.info(f"共注册 {len(self.skills)} 个技能")

    def get_skill(self, name: str) -> Optional[SkillMetadata]:
        """获取技能元数据"""
        return self.skills.get(name)

    def list_skills(self) -> List[Dict]:
        """列出所有技能"""
        return [
            {
                "name": s.name,
                "version": s.version,
                "description": s.description[:100],
                "security_grade": s.security_grade,
                "enabled": s.enabled,
            }
            for s in self.skills.values()
        ]

    def execute_skill(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行技能"""
        if name not in self.skills:
            return {"success": False, "error": f"技能 '{name}' 未注册"}

        skill = self.skills[name]
        script_path = Path(skill.path) / "scripts" / "main.py"

        if not script_path.exists():
            return {"success": False, "error": f"技能脚本不存在: {script_path}"}

        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(name, script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "execute"):
                return module.execute(params)
            else:
                return {"success": False, "error": f"技能 {name} 没有 execute 函数"}
        except Exception as e:
            logger.error(f"执行技能 {name} 失败: {e}")
            return {"success": False, "error": str(e)}

    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "version": self.VERSION,
            "total_skills": len(self.skills),
            "skills": [s.name for s in self.skills.values()][:20],
        }


skill_registry = SkillRegistry()


if __name__ == "__main__":
    print(f"技能注册中心 v{skill_registry.VERSION}")
    print(f"已注册: {len(skill_registry.skills)} 个技能")
    for s in skill_registry.list_all():
        print(f"  - {s['name']} v{s['version']}")
