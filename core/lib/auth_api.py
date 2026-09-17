#!/usr/bin/env python3
"""Auth Api - Auth Api 模块

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

"""认证中心 - JWT Token 管理"""

import hashlib
import json
import os

# 加载 JWT 配置(2026-09-08 P0-1): secret 一律环境变量 JWT_SECRET(.env 注入), 不读仓库内 secret。
import secrets as _sec_api
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

import jwt
import yaml
from flask import jsonify, request

JWT_SECRET = os.getenv("JWT_SECRET") or _sec_api.token_urlsafe(48)
if not os.getenv("JWT_SECRET"):
    import logging as _lg_api

    _lg_api.getLogger(__name__).warning("JWT_SECRET 未配置, auth_api 使用进程级随机 secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
# 算法/过期时长可选从 config/security/jwt.yaml 读取(不含 secret)
_SEC_FILE = Path(__file__).resolve().parent.parent.parent / "config/security/jwt.yaml"
try:
    if _SEC_FILE.exists():
        import yaml as _y_api

        with open(_SEC_FILE, "r", encoding="utf-8") as _f_api:
            _jc_api = _y_api.safe_load(_f_api) or {}
        JWT_ALGORITHM = _jc_api.get("algorithm", "HS256")
        JWT_EXPIRY_HOURS = int(_jc_api.get("expire_hours", 24))
except Exception:
    pass

# 用户数据存储
USER_DB = Path(f"{get_data_root()}/users.db.json")
USER_DB.parent.mkdir(parents=True, exist_ok=True)


class AuthManager:
    """认证管理器"""

    def __init__(self):
        self._load_users()

    def _load_users(self):
        if USER_DB.exists():
            with open(USER_DB, "r", encoding="utf-8") as f:
                self.users = json.load(f)
        else:
            self.users = {}

    def _save_users(self):
        with open(USER_DB, "w", encoding="utf-8") as f:
            json.dump(self.users, f, indent=2)

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def _generate_token(self, user_id: str, username: str, role: str = "user") -> str:
        payload = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def register(self, username: str, password: str, role: str = "user") -> dict:
        if username in self.users:
            return {"success": False, "error": "用户名已存在"}

        if not username or not password:
            return {"success": False, "error": "用户名和密码不能为空"}

        user_id = hashlib.md5(f"{username}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]

        self.users[username] = {
            "user_id": user_id,
            "username": username,
            "password_hash": self._hash_password(password),
            "role": role,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "status": "active",
        }

        # 创建租户目录
        tenant_dir = Path(f"{get_data_root()}/tenants/{user_id}")
        tenant_dir.mkdir(parents=True, exist_ok=True)

        self._save_users()
        token = self._generate_token(user_id, username, role)

        return {
            "success": True,
            "user_id": user_id,
            "username": username,
            "role": role,
            "token": token,
        }

    def login(self, username: str, password: str) -> dict:
        if username not in self.users:
            return {"success": False, "error": "用户不存在"}

        user = self.users[username]
        if user["password_hash"] != self._hash_password(password):
            return {"success": False, "error": "密码错误"}

        if user["status"] != "active":
            return {"success": False, "error": "账户已禁用"}

        user["last_login"] = datetime.now().isoformat()
        self._save_users()

        token = self._generate_token(user["user_id"], username, user["role"])

        return {
            "success": True,
            "user_id": user["user_id"],
            "username": username,
            "role": user["role"],
            "token": token,
        }

    def verify_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


auth_manager = AuthManager()
