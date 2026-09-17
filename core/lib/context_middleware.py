#!/usr/bin/env python3
"""Context Middleware - Context Middleware 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""请求上下文中间件 - 自动注入 user_id 和 tenant_id"""
import os

import jwt
from flask import g, request

SECRET_KEY = os.environ.get("JWT_SECRET", "clawsjoy-secret-key")


def load_user_context():
    g.user_id = None
    g.tenant_id = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            g.user_id = payload.get("user_id") or payload.get("username")
            g.tenant_id = payload.get("tenant_id")
        except Exception as e:
            pass
    if not g.user_id and request.is_json:
        data = request.get_json(silent=True) or {}
        g.user_id = data.get("user_id")
        g.tenant_id = data.get("tenant_id")
    if not g.user_id:
        g.user_id = "default"
    if not g.tenant_id:
        g.tenant_id = g.user_id
