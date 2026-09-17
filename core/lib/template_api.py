#!/usr/bin/env python3
"""Template Api - Template Api 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""配置模板 API - 一键导入配置模板"""

import shutil
from pathlib import Path

import yaml
from flask import jsonify, request

TEMPLATES_DIR = Path("config/templates")
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def register_template_routes(app):

    @app.route("/api/templates/list", methods=["GET"])
    def list_templates():
        """列出所有模板"""
        templates = []
        for f in TEMPLATES_DIR.glob("*.yaml"):
            with open(f, "r") as file:
                content = unified_config.get("templates", {})
                templates.append(
                    {
                        "name": f.stem,
                        "description": content.get("description", ""),
                        "version": content.get("version", "1.0.0"),
                        "file": f.name,
                    }
                )
        return jsonify({"templates": templates})

    @app.route("/api/templates/<name>", methods=["GET"])
    def get_template(name):
        """获取模板详情"""
        template_file = TEMPLATES_DIR / f"{name}.yaml"
        if not template_file.exists():
            return jsonify({"error": "模板不存在"}), 404

        with open(template_file, "r") as f:
            content = unified_config.get("template_api", {})
        return jsonify({"template": content})

    @app.route("/api/templates/<name>/apply", methods=["POST"])
    def apply_template(name):
        """应用模板到当前配置"""
        from flask import g, request

        from core.lib.auth_api import require_auth

        template_file = TEMPLATES_DIR / f"{name}.yaml"
        if not template_file.exists():
            return jsonify({"error": "模板不存在"}), 404

        with open(template_file, "r") as f:
            template = unified_config.get("template_api", {})

        target_type = request.json.get("target", "agent")

        if target_type == "agent":
            # 应用到 agents.yaml
            agents_file = Path("config/agents.yaml")
            with open(agents_file, "r") as f:
                agents_config = unified_config.get("template_api", {})

            agent_name = template.get("name", name)
            agents_config["agents"][agent_name] = template.get("config", {})

            with open(agents_file, "w") as f:
                yaml.dump(agents_config, f)

        return jsonify(
            {"success": True, "message": f"模板 {name} 已应用", "template": template}
        )

    print("✅ 模板 API 已注册")
