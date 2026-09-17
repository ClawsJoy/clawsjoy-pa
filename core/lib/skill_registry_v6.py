"""
Skill Registry V6 — 桥接层
让旧代码调 skill_registry 时实际走 v6.0 YAML 注册中心
"""
import yaml
from pathlib import Path
from typing import Dict, List, Optional


class SkillRegistryV6:
    """v6.0 统一 Skill 注册中心"""

    VERSION = "6.0.0"

    def __init__(self):
        self.skills: Dict[str, dict] = {}
        self._load_from_yaml()

    def _load_from_yaml(self):
        """从 config/capabilities/skills/*.yaml 加载"""
        skill_dir = Path("config/capabilities/skills")
        if not skill_dir.exists():
            return

        for yf in skill_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(yf.read_text())
                name = data.get("name", yf.stem)
                if not data.get("actions"):
                    continue
                self.skills[name] = {
                    "name": name,
                    "description": data.get("description", ""),
                    "actions": data.get("actions", []),
                    "type": data.get("type", "skill"),
                    "path": str(Path("skills") / name),
                }
            except Exception:
                pass

    # === 兼容旧接口 ===

    def get(self, name: str, default=None):
        """兼容 skill_registry.get()"""
        return self.skills.get(name, default)

    def get_skill(self, name: str) -> Optional[dict]:
        return self.skills.get(name)

    def list_skills(self) -> List[str]:
        return list(self.skills.keys())

    def list_all(self) -> List[dict]:
        return [
            {"name": s["name"], "version": "6.0", "description": s["description"]}
            for s in self.skills.values()
        ]

    def execute_skill(self, name: str, params: dict) -> dict:
        """执行 Skill — 委托给 executor_agent"""
        try:
            from agents.executor_agent.agent_v4 import ExecutorAgentV4
            executor = ExecutorAgentV4("system")
            return executor._exec_skill(name)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_stats(self) -> dict:
        return {"version": self.VERSION, "total_skills": len(self.skills)}

    @property
    def skills_dict(self):
        """兼容旧 .skills 属性"""
        return self.skills


# 全局单例
skill_registry = SkillRegistryV6()
