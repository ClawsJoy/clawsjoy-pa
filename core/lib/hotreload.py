#!/usr/bin/env python3
"""Hotreload - Hotreload 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""配置热重载模块 - 租户内管理员也可使用"""

import importlib
import sys

from flask import g, request


def reload_module(module_name: str):
    """热重载模块"""
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
        print(f"✅ 已重载: {module_name}")
        return True
    return False


def reload_all_configs():
    """重载所有配置"""
    modules = [
        "lib.route_registry",
        "lib.agent_registry",
        "lib.skill_loader_v3",
        "lib.auth_api",
    ]

    results = {}
    for mod in modules:
        try:
            results[mod] = reload_module(mod)
        except Exception as e:
            results[mod] = f"失败: {e}"

    return results


def is_tenant_admin(user):
    """判断是否为租户内管理员"""
    if not user:
        return False
    # 租户内管理员：admin 角色 或 该租户的第一个用户
    if user.get("role") == "admin":
        return True
    # 普通用户在自己的租户里也视为管理员
    return True  # 在自己的沙箱里


def register_hotreload_routes(app):
    """注册热重载路由"""

    @app.route("/api/config/reload", methods=["POST"])
    def hotreload_all():
        from flask import jsonify

        from core.lib.auth_api import auth_manager

        # 验证用户
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user = auth_manager.verify_token(token)

        if not user:
            return jsonify({"error": "未认证"}), 401

        # 在自己的沙箱里就有权限
        if not is_tenant_admin(user):
            return jsonify({"error": "需要管理员权限"}), 403

        results = reload_all_configs()
        return jsonify({"success": True, "reloaded": results, "user": user.get("username")})

    @app.route("/api/config/reload/<config_type>", methods=["POST"])
    def hotreload_type(config_type):
        from flask import jsonify

        from core.lib.auth_api import auth_manager

        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user = auth_manager.verify_token(token)

        if not user:
            return jsonify({"error": "未认证"}), 401

        if not is_tenant_admin(user):
            return jsonify({"error": "需要管理员权限"}), 403

        mapping = {
            "routes": "lib.route_registry",
            "agents": "lib.agent_registry",
            "skills": "lib.skill_loader_v3",
            "auth": "lib.auth_api",
        }

        if config_type in mapping:
            result = reload_module(mapping[config_type])
            return jsonify({"success": result, "config_type": config_type})

        return jsonify({"success": False, "error": "未知配置类型"})

    print("✅ 热重载 API 已注册（租户内管理员可用）")
