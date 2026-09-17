# -*- coding: utf-8 -*-
"""安全中间件(2026-09-08 GPT-6 阶段0 止血 P0-3/P0-4) — 过渡方案

P0-4: /v9/sandbox/* 只允许本机环回(127.0.0.1/::1), 外部请求 403。
P0-3: 环回默认放行; 非环回请求强制 JWT 认证(Authorization: Bearer), 失败 401;
      认证通过后 user_id 一律以 claims 为准 — 请求体 user_id 与凭证不符 → 403,
      请求体缺 user_id 时从 claims 注入(资源归属不能由请求体决定)。
环境开关: AUTH_EXTERNAL_REQUIRE=0 可临时关闭外部强制认证(不推荐)。
"""
import os

_LOOPBACK_PREFIXES = ("127.",)
_LOOPBACK_HOSTS = ("127.0.0.1", "::1", "localhost")


def _is_loopback(remote_addr):
    rip = str(remote_addr or "").strip()
    if not rip:
        return False
    return rip in _LOOPBACK_HOSTS or rip.startswith(_LOOPBACK_PREFIXES)


def check_access(path, remote_addr, auth_header="", body=None, env=None):
    """纯判定: 返回 (http_code|None, error|None)。

    None code = 放行; code 403/401 = 拦截。
    """
    env = env if env is not None else os.environ
    path = path or ""
    loopback = _is_loopback(remote_addr)
    if path.startswith("/v9/sandbox"):
        if not loopback:
            return 403, "403: /v9/sandbox/* 仅允许本机环回访问"
        return None, None
    if loopback:
        return None, None
    if str(env.get("AUTH_EXTERNAL_REQUIRE", "1")) == "0":
        return None, None
    auth = str(auth_header or "")
    if not auth.startswith("Bearer "):
        return 401, "401: 外部访问需认证(Authorization: Bearer <JWT>)"
    try:
        from core.lib.auth_middleware import get_auth_manager
        payload = get_auth_manager().verify_jwt(auth[7:])
    except Exception:
        payload = None
    if not payload:
        return 401, "401: 无效或过期凭证"
    claims_uid = str(payload.get("user_id") or "")
    if body and claims_uid:
        body_uid = body.get("user_id")
        if body_uid and str(body_uid) != claims_uid:
            return 403, "403: 请求体 user_id 与认证凭证不符(资源归属以凭证为准)"
        if not body_uid:
            body["user_id"] = claims_uid
    return None, None


def register_security_middleware(app):
    """注册全局安全门: sandbox 限环回 + 外部强制认证(过渡)。"""

    @app.before_request
    def _security_gate():
        from flask import g as _g, jsonify, request
        code, err = check_access(request.path or "", request.remote_addr or "",
                                 request.headers.get("Authorization", ""),
                                 request.get_json(silent=True) if request.is_json else None)
        if code:
            return jsonify({"success": False, "error": err}), code
        return None

    print("✅ 安全中间件已注册(沙箱限环回 + 外部强制认证)")
