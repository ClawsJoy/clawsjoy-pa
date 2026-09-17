"""OpenClaw 社区兼容引擎 - 技能市场同步"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yaml

from engine.lib.logger import engine_logger


class OpenClawEngine:
    """OpenClaw 社区兼容引擎 - 技能双向同步"""

    COMMUNITY_API = "https://openclaw.community/api"

    def __init__(self):
        self.sync_file = Path("data/openclaw_sync.json")
        self.export_dir = Path("data/openclaw_exports")
        self.import_dir = Path("data/openclaw_imports")
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.import_dir.mkdir(parents=True, exist_ok=True)
        self._load_sync_state()
        engine_logger.get().info("🔌 OpenClaw 社区引擎已初始化")

    def _load_sync_state(self):
        if self.sync_file.exists():
            with open(self.sync_file, "r") as f:
                self.state = json.load(f)
        else:
            self.state = {
                "last_sync": None,
                "exported_skills": [],
                "imported_skills": [],
                "pending_exports": [],
            }

    def _save_sync_state(self):
        with open(self.sync_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def export_skill(self, skill_name: str, skill_data: Dict) -> Dict:
        manifest = {
            "name": skill_name,
            "version": skill_data.get("version", "1.0.0"),
            "type": "atomic",
            "description": skill_data.get("description", ""),
            "category": skill_data.get("category", "general"),
            "author": "ClawsJoy",
            "openclaw_version": "1.0.0",
            "compatibility": "full",
            "exported_at": datetime.now().isoformat(),
            "dependencies": skill_data.get("dependencies", []),
            "input_schema": skill_data.get("input_schema", {}),
            "output_schema": skill_data.get("output_schema", {}),
        }

        export_file = self.export_dir / f"{skill_name}.json"
        with open(export_file, "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        skill_md = self.export_dir / f"{skill_name}.md"
        skill_md.write_text(self._generate_skill_md(manifest))

        if skill_name not in self.state["exported_skills"]:
            self.state["exported_skills"].append(skill_name)
        self._save_sync_state()

        engine_logger.get().info(f"   📤 导出技能: {skill_name}")
        return {"success": True, "file": str(export_file), "manifest": manifest}

    def _generate_skill_md(self, manifest: Dict) -> str:
        return f"""---
name: {manifest['name']}
version: {manifest['version']}
description: '{manifest['description']}'
category: {manifest['category']}
author: ClawsJoy
openclaw_version: {manifest['openclaw_version']}
---

# {manifest['name']}

{manifest['description']}

## 参数
{self._format_params(manifest.get('input_schema', {}))}

## 返回值
{self._format_output(manifest.get('output_schema', {}))}
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

    def import_skill(self, skill_name: str, source: str = None) -> Dict:
        if source == "file":
            import_file = self.import_dir / f"{skill_name}.json"
        else:
            import_file = self.export_dir / f"{skill_name}.json"

        if not import_file.exists():
            return {"success": False, "error": f"Skill {skill_name} not found"}

        with open(import_file, "r") as f:
            manifest = json.load(f)

        skill_dir = Path(f"skills/{skill_name}")
        skill_dir.mkdir(exist_ok=True)

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(self._generate_skill_md(manifest))

        manifest_file = skill_dir / "manifest.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)

        if skill_name not in self.state["imported_skills"]:
            self.state["imported_skills"].append(skill_name)
        self._save_sync_state()

        engine_logger.get().info(f"   📥 导入技能: {skill_name}")
        return {"success": True, "skill": skill_name, "manifest": manifest}

    def sync_with_community(self, direction: str = "both") -> Dict:
        result = {
            "exported": [],
            "imported": [],
            "errors": [],
            "timestamp": datetime.now().isoformat(),
        }

        if direction in ["export", "both"]:
            try:
                from engine.skill_matrix.core import skill_matrix_engine

                for skill_name in list(skill_matrix_engine.skills.keys())[:50]:
                    skill = skill_matrix_engine.skills.get(skill_name)
                    if skill:
                        export_result = self.export_skill(
                            skill_name,
                            {
                                "description": skill.get("description", ""),
                                "category": skill.get("category", "general"),
                            },
                        )
                        if export_result.get("success"):
                            result["exported"].append(skill_name)
            except Exception as e:
                result["errors"].append(f"Export error: {e}")

        if direction in ["import", "both"]:
            for json_file in self.export_dir.glob("*.json"):
                skill_name = json_file.stem
                if skill_name not in self.state["imported_skills"]:
                    try:
                        self.import_skill(skill_name, "file")
                        result["imported"].append(skill_name)
                    except Exception as e:
                        result["errors"].append(f"Import {skill_name}: {e}")

        self.state["last_sync"] = result["timestamp"]
        self._save_sync_state()

        engine_logger.get().info(
            f"   🔄 同步完成: 导出 {len(result['exported'])}, 导入 {len(result['imported'])}"
        )
        return result

    def list_exported(self) -> List[str]:
        return self.state["exported_skills"]

    def list_imported(self) -> List[str]:
        return self.state["imported_skills"]

    def reload(self) -> Dict:
        """热重载配置"""
        self._load_sync_state()
        return {"success": True, "message": "OpenClaw engine reloaded"}

    def health_check(self) -> Dict:
        """健康检查"""
        return {"name": "openclaw_engine", "status": "healthy"}

    def get_stats(self) -> Dict:
        return {
            "exported_skills": len(self.state["exported_skills"]),
            "imported_skills": len(self.state["imported_skills"]),
            "last_sync": self.state["last_sync"],
            "sync_ready": True,
            "openclaw_version": "1.0.0",
        }

    def process(self, input_data: Any = None, **kwargs) -> Any:
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, str):
            if input_data == "sync":
                return self.sync_with_community()
            return self.import_skill(input_data)
        if isinstance(input_data, dict):
            action = input_data.get("action", "sync")
            if action == "export":
                return self.export_skill(
                    input_data.get("name"), input_data.get("data", {})
                )
            elif action == "import":
                return self.import_skill(input_data.get("name"))
            elif action == "sync":
                return self.sync_with_community(input_data.get("direction", "both"))
        return self.sync_with_community()


openclaw_engine = OpenClawEngine()
