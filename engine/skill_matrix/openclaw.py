"""OpenClaw 社区兼容层 - 双向兼容"""

import json
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

import yaml


class OpenClawCompatibility:
    """OpenClaw 社区规范兼容"""

    def __init__(self):
        self.openclaw_spec_version = "1.0.0"
        print("🔌 OpenClaw 兼容层已初始化")

    def export_to_openclaw(self, skill_name: str) -> Dict:
        """导出技能为 OpenClaw 格式"""
        skill_path = Path(f"skills/{skill_name}")
        if not skill_path.exists():
            skill_path = Path(f"marketplace/skills/{skill_name}")

        manifest = {
            "name": skill_name,
            "type": "atomic",
            "version": "1.0.0",
            "openclaw_version": self.openclaw_spec_version,
            "compatibility": "full",
            "exported_at": datetime.now().isoformat(),
        }

        # 读取 SKILL.md
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            for line in content.split("\n"):
                if line.startswith("description:"):
                    manifest["description"] = line.replace("description:", "").strip()
                    break
                if line.startswith("security_grade:"):
                    manifest["security_grade"] = line.replace(
                        "security_grade:", ""
                    ).strip()

        # 读取 manifest.json
        manifest_file = skill_path / "manifest.json"
        if manifest_file.exists():
            with open(manifest_file, "r") as f:
                data = json.load(f)
                manifest.update(data)

        return manifest

    def import_from_openclaw(self, skill_manifest: Dict) -> bool:
        """从 OpenClaw 导入技能"""
        if not self._validate_openclaw_format(skill_manifest):
            return False

        skill_name = skill_manifest.get("name")
        if not skill_name:
            return False

        # 创建技能目录
        skill_dir = Path(f"skills/{skill_name}")
        skill_dir.mkdir(exist_ok=True)

        # 创建 SKILL.md
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(self._generate_skill_md(skill_manifest))

        # 创建 manifest.json
        manifest_file = skill_dir / "manifest.json"
        with open(manifest_file, "w") as f:
            json.dump(skill_manifest, f, indent=2)

        print(f"✅ 从 OpenClaw 导入技能: {skill_name}")
        return True

    def _validate_openclaw_format(self, skill: Dict) -> bool:
        """验证 OpenClaw 格式"""
        required = ["name", "version"]
        return all(r in skill for r in required)

    def _generate_skill_md(self, skill: Dict) -> str:
        """生成 SKILL.md"""
        security_grade = skill.get("security_grade", "A")
        return f"""---
name: {skill.get('name')}
version: {skill.get('version', '1.0.0')}
description: '{skill.get('description', '')}'
author: {skill.get('author', 'OpenClaw')}
security_grade: {security_grade}
---

# {skill.get('name')}

{skill.get('description', '')}

## 参数
{self._format_params(skill.get('input_schema', {}))}

## 返回值
{self._format_output(skill.get('output_schema', {}))}
"""

    def _format_params(self, schema: Dict) -> str:
        if not schema:
            return "无参数"
        lines = ["| 参数 | 类型 | 必填 | 描述 |", "|------|------|------|------|"]
        for name, info in schema.items():
            required = "是" if info.get("required") else "否"
            lines.append(
                f"| {name} | {info.get('type', 'string')} | {required} | {info.get('description', '')} |"
            )
        return "\n".join(lines)

    def _format_output(self, schema: Dict) -> str:
        if not schema:
            return "| 字段 | 类型 | 描述 |\n|------|------|------|\n| success | boolean | 是否成功 |"
        lines = ["| 字段 | 类型 | 描述 |", "|------|------|------|"]
        for name, info in schema.items():
            lines.append(
                f"| {name} | {info.get('type', 'string')} | {info.get('description', '')} |"
            )
        return "\n".join(lines)

    def sync_with_community(self) -> Dict:
        """与社区同步"""
        local_skills = []
        skills_dir = Path("skills")
        if skills_dir.exists():
            for d in skills_dir.iterdir():
                if d.is_dir() and not d.name.startswith("_"):
                    local_skills.append(d.name)

        return {
            "local_skills": len(local_skills),
            "skill_list": local_skills[:30],
            "openclaw_version": self.openclaw_spec_version,
            "sync_status": "ready",
        }


openclaw_compat = OpenClawCompatibility()
