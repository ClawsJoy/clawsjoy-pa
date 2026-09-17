#!/usr/bin/env python3
"""Tenant Middleware - Tenant Middleware 模块

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

"""租户上下文中间件 - 自动注入 tenant_id"""

import os
from functools import wraps
from pathlib import Path

import jwt
from flask import g, request

JWT_SECRET = os.environ.get("JWT_SECRET", "clawsjoy-secret-key-change-in-production")


def get_tenant_from_token():
    """从 JWT Token 中提取租户 ID"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("tenant_id") or payload.get("user_id")
    except Exception as e:
        return None


def get_tenant_from_header():
    """从请求头获取租户 ID"""
    return request.headers.get("X-Tenant-Id")


def ensure_tenant_directory(tenant_id: str):
    """确保租户目录存在"""
    if not tenant_id:
        return
    tenant_dir = Path(f"{get_data_root()}/tenants/{tenant_id}")
    tenant_dir.mkdir(parents=True, exist_ok=True)


def tenant_middleware():
    """租户中间件 - 在每个请求前执行"""
    tenant_id = get_tenant_from_header() or get_tenant_from_token()

    if not tenant_id:
        tenant_id = "default"

    g.tenant_id = tenant_id
    ensure_tenant_directory(tenant_id)

    # 添加到响应头
    from flask import after_this_request

    @after_this_request
    def add_tenant_header(response):
        response.headers["X-Tenant-Id"] = tenant_id
        return response


def register_tenant_middleware(app):
    """注册租户中间件"""

    @app.before_request
    def before_request():
        tenant_middleware()

    print("✅ 租户中间件已注册")
