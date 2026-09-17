# -*- coding: utf-8 -*-
"""用户认证路由（P3-A 拆出，Blueprint）—— 注册 / 登录"""

from datetime import datetime

from flask import Blueprint, jsonify, request

bp = Blueprint("auth_routes", __name__)


@bp.route("/api/user/register", methods=["POST"])
def user_register():
    from core.lib.auth_api import AuthManager

    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    if not username or not password:
        return jsonify({"success": False, "error": "用户名和密码不能为空"}), 400
    result = AuthManager().register(username, password, role="user")
    if result.get("success"):
        from core.lib.gateway_helpers import create_user_directories

        create_user_directories(username, result["user_id"])
    return jsonify(result)


@bp.route("/api/user/login", methods=["POST"])
def user_login():
    from core.lib.auth_api import AuthManager

    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    if not username or not password:
        return jsonify({"success": False, "error": "用户名和密码不能为空"}), 400
    auth = AuthManager()
    if username not in auth.users:
        return jsonify({"success": False, "error": "用户不存在"}), 401
    user = auth.users[username]
    if user["password_hash"] != auth._hash_password(password):
        return jsonify({"success": False, "error": "密码错误"}), 401
    token = auth._generate_token(user["user_id"], username, user.get("role", "user"))
    user["last_login"] = datetime.now().isoformat()
    auth._save_users()
    return jsonify(
        {
            "success": True,
            "token": token,
            "user_id": user["user_id"],
            "username": username,
            "role": user.get("role", "user"),
        }
    )
