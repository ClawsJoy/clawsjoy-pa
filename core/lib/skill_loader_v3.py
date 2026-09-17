#!/usr/bin/env python3
"""技能加载器 V3 - 支持多种技能定义方式"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional


class SkillLoaderV3:
    """技能加载器 V3 - 支持 SKILL.md、manifest.json、装饰器等多种定义"""

    def __init__(self):
        self.skills = {}
        self.categories = {}
        self._load_all()

    def _load_all(self):
        """加载所有技能"""
        # 1. 扫描 SKILL.md
        self._load_from_skill_md()

        # 2. 扫描 manifest.json

        # 3. 扫描 *_skill.py 文件
        # self._load_from_skill_files()  # 已在 SKILL.md 中处理

        # 4. 扫描 core/skills/ 目录

        # 5. 扫描 agents 作为技能

        print(f"✅ 技能加载完成，共 {len(self.skills)} 个技能")

    def _load_from_skill_md(self):
        """从 SKILL.md 文件加载技能"""
        for skill_md in Path("skills").rglob("SKILL.md"):
            if "site-packages" in str(skill_md) or "__pycache__" in str(skill_md):
                continue

            name = skill_md.parent.name
            # 检查必需文件是否存在
            init_file = skill_md.parent / "__init__.py"
            skill_file = skill_md.parent / f"{name}_skill.py"
            if not init_file.exists() or not skill_file.exists():
                continue
            if name in self.skills:
                continue

            category = "general"
            description = ""

            try:
                with open(skill_md, "r", encoding="utf-8") as f:
                    content = f.read()

                # 提取 category
                for line in content.split("\n"):
                    if line.startswith("category:"):
                        category = line.split(":", 1)[1].strip()
                        break
                    if line.startswith("description:"):
                        description = line.split(":", 1)[1].strip()
            except Exception as e:
                pass

            self.skills[name] = {
                "name": name,
                "category": category,
                "description": description,
                "file": str(skill_md),
                "source": "SKILL.md",
                "type": "skill_md",
            }
            self._add_to_category(category, name)

    def _load_from_manifest(self):
        """从 manifest.json 文件加载技能"""
        for manifest_file in Path("skills").rglob("manifest.json"):
            if "site-packages" in str(manifest_file) or "__pycache__" in str(
                manifest_file
            ):
                continue

            try:
                with open(manifest_file, "r") as f:
                    data = json.load(f)

                name = data.get("name", manifest_file.parent.name)
                if name in self.skills:
                    continue

                category = data.get("category", "general")
                description = data.get("description", "")

                self.skills[name] = {
                    "name": name,
                    "category": category,
                    "description": description,
                    "file": str(manifest_file),
                    "source": "manifest.json",
                    "type": "manifest",
                }
                self._add_to_category(category, name)
            except Exception as e:
                pass

    def _load_from_skill_files(self):
        """从 *_skill.py 文件加载技能"""
        for py_file in Path(".").rglob("*_skill.py"):
            if "site-packages" in str(py_file) or "__pycache__" in str(py_file):
                continue

            name = py_file.stem
            if name in self.skills:
                continue

            # 提取描述
            description = ""
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    for line in content.split("\n"):
                        if '"""' in line and not description:
                            desc = line.strip(' """').strip()
                            if desc and len(desc) > 5:
                                description = desc[:100]
                                break
            except Exception as e:
                pass

            self.skills[name] = {
                "name": name,
                "category": "skill_file",
                "description": description,
                "file": str(py_file),
                "source": "skill_file",
                "type": "skill_file",
            }
            self._add_to_category("skill_file", name)

    def _load_from_core_skills(self):
        """从 core/skills/ 目录加载"""
        core_skills = Path("core/skills")
        if not core_skills.exists():
            return

        for py_file in core_skills.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            name = py_file.stem
            if name in self.skills:
                continue

            # 提取描述
            description = ""
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    for line in content.split("\n"):
                        if '"""' in line and not description:
                            desc = line.strip(' """').strip()
                            if desc and len(desc) > 5:
                                description = desc[:100]
                                break
            except Exception as e:
                pass

            self.skills[name] = {
                "name": name,
                "category": "core",
                "description": description,
                "file": str(py_file),
                "source": "core/skills",
                "type": "core",
            }
            self._add_to_category("core", name)

    def _load_from_agents(self):
        """从 agents 目录加载技能"""
        agents_dir = Path("core/agents/builtin")
        if not agents_dir.exists():
            return

        for agent_file in agents_dir.glob("*_agent.py"):
            name = agent_file.stem
            if name in self.skills:
                continue

            # 提取描述
            description = ""
            try:
                with open(agent_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    for line in content.split("\n"):
                        if '"""' in line and not description:
                            desc = line.strip(' """').strip()
                            if desc and len(desc) > 5:
                                description = desc[:100]
                                break
            except Exception as e:
                pass

            self.skills[name] = {
                "name": name,
                "category": "agent",
                "description": description,
                "file": str(agent_file),
                "source": "agents",
                "type": "agent",
            }
            self._add_to_category("agent", name)

    def _add_to_category(self, category: str, skill_name: str):
        """添加到分类"""
        if category not in self.categories:
            self.categories[category] = []
        if skill_name not in self.categories[category]:
            self.categories[category].append(skill_name)

    def list_skills(self, category: str = None) -> Dict:
        """列出所有技能"""
        if category and category in self.categories:
            return {s: self.skills[s] for s in self.categories[category]}
        return self.skills

    def get_skill(self, name: str) -> Optional[Dict]:
        """获取技能信息"""
        return self.skills.get(name)

    def execute(self, skill_name: str, params: dict) -> dict:
        """执行技能"""
        try:
            import importlib

            skill_info = self.get_skill(skill_name)
            if not skill_info:
                return {"error": f"技能 {skill_name} 不存在"}

            # 尝试不同的模块路径
            module_paths = [
                f"skills.{skill_name}",
                f"skills.{skill_info.get('category', 'general')}.{skill_name}",
                f"core.skills.{skill_name}",
                f"core.agents.builtin.{skill_name}",
            ]

            for module_path in module_paths:
                try:
                    module = importlib.import_module(module_path)
                    if hasattr(module, "execute"):
                        return module.execute(params)
                    elif hasattr(module, "run"):
                        return module.run(params)
                except ImportError:
                    continue

            return {"error": f"技能 {skill_name} 无法执行"}
        except Exception as e:
            return {"error": str(e)}

    def search_skills(self, keyword: str) -> list:
        """搜索技能"""
        results = []
        keyword_lower = keyword.lower()
        for name, info in self.skills.items():
            if (
                keyword_lower in name.lower()
                or keyword_lower in info.get("category", "").lower()
            ):
                results.append(info)
        return results

    def get_categories(self) -> Dict:
        """获取分类"""
        return self.categories

    def reload(self):
        """重新加载所有技能"""
        self.skills = {}
        self.categories = {}
        self._load_all()


_skill_loader = None


def get_skill_loader():
    global _skill_loader
    if _skill_loader is None:
        _skill_loader = LazySkillLoader()
    return _skill_loader


skill_loader = None


class LazySkillLoader(SkillLoaderV3):
    """懒加载技能加载器"""

    _instance = None
    _skills = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_skill(self, name):
        if self._skills is None:
            self._load()
        return self._skills.get(name)

    def _load(self):
        # 延迟加载
        pass
