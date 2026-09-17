#!/usr/bin/env python3
"""Tenant Config Api - Tenant Config Api 模块

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

"""租户配置 API - 多租户隔离配置管理"""

import json
from pathlib import Path

import yaml
from flask import g, jsonify, request

from core.lib.auth_api import require_auth, require_role


def get_tenant_config_dir():
    """获取租户配置目录"""
    tenant_id = getattr(g, "tenant_id", "default")
    tenant_dir = Path(f"{get_data_root()}/tenants/{tenant_id}/config")
    tenant_dir.mkdir(parents=True, exist_ok=True)
    return tenant_dir


def register_tenant_config_routes(app):

    @app.route("/api/tenant/config", methods=["GET"])
    @require_auth
    def get_tenant_config():
        """获取租户配置"""
        tenant_dir = get_tenant_config_dir()
        config_file = tenant_dir / "settings.yaml"
        config = {}
        if config_file.exists():
            with open(config_file, "r") as f:
                config = unified_config.get("tenant_api", {})
        return jsonify({"success": True, "config": config, "tenant_id": g.tenant_id})

    @app.route("/api/tenant/config", methods=["POST"])
    @require_auth
    @require_role("developer")
    def update_tenant_config():
        """更新租户配置（开发者及以上）"""
        tenant_dir = get_tenant_config_dir()
        config_file = tenant_dir / "settings.yaml"
        data = request.json
        new_config = data.get("config", {})

        # 加载现有配置
        existing = {}
        if config_file.exists():
            with open(config_file, "r") as f:
                existing = unified_config.get("tenant_api", {}) or {}

        # 合并配置
        existing.update(new_config)

        with open(config_file, "w") as f:
            yaml.dump(existing, f)

        return jsonify(
            {"success": True, "message": "租户配置已更新", "tenant_id": g.tenant_id}
        )

    @app.route("/api/tenant/config/<key>", methods=["GET"])
    @require_auth
    def get_tenant_config_key(key):
        """获取租户配置的特定键值"""
        tenant_dir = get_tenant_config_dir()
        config_file = tenant_dir / "settings.yaml"
        config = {}
        if config_file.exists():
            with open(config_file, "r") as f:
                config = unified_config.get("tenant_api", {}) or {}
        return jsonify(
            {
                "success": True,
                "key": key,
                "value": config.get(key),
                "tenant_id": g.tenant_id,
            }
        )

    @app.route("/api/tenant/config/<key>", methods=["POST"])
    @require_auth
    @require_role("developer")
    def set_tenant_config_key(key):
        """设置租户配置的特定键值"""
        tenant_dir = get_tenant_config_dir()
        config_file = tenant_dir / "settings.yaml"
        data = request.json
        value = data.get("value")

        # 加载现有配置
        config = {}
        if config_file.exists():
            with open(config_file, "r") as f:
                config = unified_config.get("tenant_api", {}) or {}

        config[key] = value

        with open(config_file, "w") as f:
            yaml.dump(config, f)

        return jsonify(
            {"success": True, "key": key, "value": value, "tenant_id": g.tenant_id}
        )

    @app.route("/api/tenant/config/reset", methods=["POST"])
    @require_auth
    @require_role("admin")
    def reset_tenant_config():
        """重置租户配置（仅管理员）"""
        tenant_dir = get_tenant_config_dir()
        config_file = tenant_dir / "settings.yaml"
        if config_file.exists():
            config_file.unlink()
        return jsonify(
            {"success": True, "message": "租户配置已重置", "tenant_id": g.tenant_id}
        )

    print("✅ 租户配置 API 已注册")


# DEPRECATED: 请使用 unified_config 代替
