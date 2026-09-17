#!/usr/bin/env python3
"""Config Api - Config Api 模块

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

"""配置管理 API - 多租户 + 零代码"""
import json
from pathlib import Path

import yaml
from flask import g, jsonify, request

from core.lib.auth_api import require_auth, require_role

# 系统级配置（所有租户共享）
SYSTEM_CONFIGS = {
    "routes": "config/routes/routes.yaml",
    "agents": "config/agents.yaml",
    "skills": "config/skill_categories.yaml",
    "hooks": "config/hooks.yaml",
    "llm": "config/llm_config.yaml",
}

# 租户级配置（可覆盖系统配置）
TENANT_CONFIGS = {
    "preferences": "preferences.yaml",
    "skills_override": "skills_override.yaml",
}


def get_tenant_config_dir():
    """获取租户配置目录"""
    tenant_id = getattr(g, "tenant_id", "default")
    tenant_dir = Path(f"{get_data_root()}/tenants/{tenant_id}/config")
    tenant_dir.mkdir(parents=True, exist_ok=True)
    return tenant_dir


def register_config_routes(app):

    @app.route("/api/config/system/<name>", methods=["GET"])
    @require_auth
    @require_role("admin")
    def get_system_config(name):
        """获取系统配置（仅管理员）"""
        if name not in SYSTEM_CONFIGS:
            return jsonify({"error": "配置不存在"}), 404
        with open(SYSTEM_CONFIGS[name], "r") as f:
            content = unified_config.get("config_api", {})
        return jsonify({"config": content, "scope": "system"})

    @app.route("/api/config/system/<name>", methods=["POST"])
    @require_auth
    @require_role("admin")
    def update_system_config(name):
        """更新系统配置（仅管理员）"""
        if name not in SYSTEM_CONFIGS:
            return jsonify({"error": "配置不存在"}), 404
        data = request.json
        with open(SYSTEM_CONFIGS[name], "w") as f:
            yaml.dump(data.get("config", {}), f)
        return jsonify({"success": True, "scope": "system"})

    @app.route("/api/config/tenant/<name>", methods=["GET"])
    @require_auth
    def get_tenant_config(name):
        """获取租户配置"""
        if name not in TENANT_CONFIGS:
            return jsonify({"error": "配置不存在"}), 404
        tenant_dir = get_tenant_config_dir()
        config_file = tenant_dir / TENANT_CONFIGS[name]
        content = {}
        if config_file.exists():
            with open(config_file, "r") as f:
                content = unified_config.get("config_api", {})
        return jsonify({"config": content, "scope": "tenant", "tenant_id": g.tenant_id})

    @app.route("/api/config/tenant/<name>", methods=["POST"])
    @require_auth
    def update_tenant_config(name):
        """更新租户配置"""
        if name not in TENANT_CONFIGS:
            return jsonify({"error": "配置不存在"}), 404
        tenant_dir = get_tenant_config_dir()
        config_file = tenant_dir / TENANT_CONFIGS[name]
        data = request.json
        with open(config_file, "w") as f:
            yaml.dump(data.get("config", {}), f)
        return jsonify({"success": True, "scope": "tenant", "tenant_id": g.tenant_id})

    @app.route("/api/config/reload", methods=["POST"])
    @require_auth
    @require_role("admin")
    def reload_config():
        """热重载配置"""
        # 触发配置重载
        from core.lib.route_registry import route_registry

        route_registry._load()
        return jsonify({"success": True})

    print("✅ 配置管理 API 已注册")


@app.route("/api/config/reload", methods=["POST"])
@require_auth
@require_role("admin")
def reload_config():
    """热重载所有配置"""
    # 重载路由
    from core.lib.route_registry import route_registry

    route_registry._load()

    # 重载 Agent 配置
    from core.lib.agent_registry import agent_registry

    agent_registry._load_config()

    # 重载技能配置
    from core.lib.skill_loader_v3 import skill_loader

    skill_loader._load_categories()

    return jsonify({"success": True, "message": "配置已热重载"})


# DEPRECATED: 请使用 unified_config 代替
