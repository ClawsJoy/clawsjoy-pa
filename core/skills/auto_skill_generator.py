#!/usr/bin/env python3
"""Auto Skill Generator - Auto Skill Generator 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
from datetime import datetime
from pathlib import Path

from core.lib.skill_loader_v3 import skill_loader


class AutoSkillGenerator:
    """自动技能生成器"""

    def __init__(self):
        self.combos_file = Path("data/skill_stats/successful_combos.json")
        self.generated_dir = Path("skills/auto_generated")
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self._load_combos()

    def _load_combos(self):
        if self.combos_file.exists():
            with open(self.combos_file, "r") as f:
                self.combos = json.load(f)
        else:
            self.combos = {"combos": [], "stats": {}}

    def analyze_and_generate(self):
        """分析并生成新技能"""
        generated = []
        combo_frequency = {}

        for combo in self.combos.get("combos", []):
            skills = combo.get("skills", [])
            if len(skills) >= 2:
                key = "|".join(skills)
                if key not in combo_frequency:
                    combo_frequency[key] = {"skills": skills, "count": 0}
                combo_frequency[key]["count"] += 1

        for key, data in combo_frequency.items():
            if data["count"] >= 3:
                skill_name = self._generate_skill_name(data["skills"])
                if not (self.generated_dir / f"{skill_name}.py").exists():
                    self._generate_skill(skill_name, data["skills"])
                    generated.append(skill_name)

        if generated:
            skill_loader._load_all()
            print(f"✅ 已生成 {len(generated)} 个新技能并热重载")

        return generated

    def _generate_skill_name(self, skills: list) -> str:
        base = skills[0] if skills else "combo"
        return f"auto_{base}_combo"

    def _generate_skill(self, skill_name: str, skills: list):
        """生成符合 OpenClaw 规范的技能（标准化参数）"""

        class_name = "".join(word.capitalize() for word in skill_name.split("_"))
        description = f"自动组合技能: {' → '.join(skills)}"

        # 生成参数映射代码
        param_mapping = self._generate_param_mapping(skills)

        code = f'''"""{description}"""

class {class_name}:
    """自动生成的组合技能 - 标准化参数传递"""

    name = "{skill_name}"
    description = "{description}"
    version = "1.0.0"
    category = "auto_generated"

    def execute(self, params):
        """执行组合技能，自动分发参数"""
        from core.lib.skill_loader_v3 import skill_loader

        results = {{}}
        context = params.copy()

{param_mapping}

        return {{
            "success": True,
            "result": results,
            "composed_of": {skills}
        }}


# 全局实例（OpenClaw 规范必需）
skill = {class_name}()
'''

        py_file = self.generated_dir / f"{skill_name}.py"
        py_file.write_text(code, encoding="utf-8")

        # 生成 SKILL.md
        self._generate_skill_md(skill_name, description, skills)

        print(f"✨ 生成新技能: {skill_name} ({' → '.join(skills)})")

    def _generate_param_mapping(self, skills: list) -> str:
        """生成参数映射代码"""
        mappings = []

        for skill in skills:
            if skill == "vision":
                mappings.append(
                    f"""        # {skill}: 需要 image_path
        if "image_path" in params or "image" in params:
            results["{skill}"] = skill_loader.execute("{skill}", {{
                "image_path": params.get("image_path") or params.get("image", ""),
                **{{k: v for k, v in params.items() if k not in ["image_path", "image"]}}
            }})
        else:
            results["{skill}"] = {{"success": False, "error": "image_path required"}}"""
                )

            elif skill == "translate_agent":
                mappings.append(
                    f"""        # {skill}: 需要 text
        if "text" in params:
            results["{skill}"] = skill_loader.execute("{skill}", {{
                "text": params.get("text", ""),
                "target": params.get("target", "zh")
            }})
        elif "result" in results and isinstance(results.get("vision"), dict):
            # 从前置技能结果中提取
            vision_result = results["vision"].get("result", "")
            if vision_result:
                results["{skill}"] = skill_loader.execute("{skill}", {{
                    "text": str(vision_result),
                    "target": params.get("target", "zh")
                }})
            else:
                results["{skill}"] = {{"success": False, "error": "no text to translate - use translate_agent"}}
        else:
            results["{skill}"] = {{"success": False, "error": "text required"}}"""
                )

            else:
                mappings.append(
                    f"""        # {skill}: 通用传递
        results["{skill}"] = skill_loader.execute("{skill}", params)"""
                )

        return "\n\n".join(mappings)

    def _generate_skill_md(self, skill_name: str, description: str, skills: list):
        """生成 SKILL.md"""
        md_file = self.generated_dir / "SKILL.md"
        existing = md_file.read_text() if md_file.exists() else ""

        skill_entry = f"""
## {skill_name}

{description}

**组合技能:** {', '.join(skills)}

**参数传递规则:**
"""
        for skill in skills:
            if skill == "vision":
                skill_entry += f"\n- {skill}: 需要 `image_path` 参数"
            elif skill == "translate_agent":
                skill_entry += (
                    f"\n- {skill}: 需要 `text` 参数，会自动从前置技能结果提取"
                )
            else:
                skill_entry += f"\n- {skill}: 接收所有参数"

        if skill_name not in existing:
            with open(md_file, "a") as f:
                f.write(skill_entry)


skill_generator = AutoSkillGenerator()
