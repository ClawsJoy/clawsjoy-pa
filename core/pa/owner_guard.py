# -*- coding: utf-8 -*-
"""PA 写路由之 owner 守卫（PM-3406 §③B · 契约：docs/design/v9_pa_owner_guard_contract_v0.md）。

一处定形：**45** 条写路由（POST/PUT/PATCH/DELETE）皆经此闸 —— ⛔ 各路由另判（二处必歧）。
判据（详见契约）：
  · 环回（127.／::1／localhost／::ffff:127.）⇒ 本机 owner ⇒ 合法；
  · 非环回 ⇒ `Authorization: Bearer <JWT>` 须过**既有二源**之一（auth_middleware／auth_api）
    且 `user_id` 非空 ⇒ 合法；
  · 余者 ⇒ **403**（fail-closed）。
⚠ 本守卫 ⛔ 取代全局安全门（`core/lib/security_middleware.py`）；二者同向：皆「本机放行 · 远端须证」。
⚠ `AUTH_EXTERNAL_REQUIRE=0` ⇒ 与全局门同义（显式关外证 ⇒ 远端亦放行）；默认 `1`。
"""
import logging
import os

from flask import jsonify, request

logger = logging.getLogger(__name__)

WRITE_METHODS = frozenset(("POST", "PUT", "PATCH", "DELETE"))
_LOOPBACK_HOSTS = ("127.0.0.1", "::1", "localhost")


def is_loopback(req):
    """环回判（与 `_loopback` 同义 · 一处出）。"""
    a = str(getattr(req, "remote_addr", "") or "").strip()
    if not a:
        return False
    if a in _LOOPBACK_HOSTS:
        return True
    if a.startswith("127."):
        return True
    if a.startswith("::ffff:") and a[7:].startswith("127."):
        return True
    return False


def _bearer(req):
    h = str((getattr(req, "headers", None) or {}).get("Authorization", "") or "")
    if h.startswith("Bearer "):
        return h[7:].strip()
    return ""


def _verify(token):
    """二源验（任一通过即返 uid；皆败返 ""）。⛔ 出新验器（承「一处定形」）。"""
    if not token:
        return ""
    try:
        from core.lib.auth_middleware import get_auth_manager as _gam
        p = _gam().verify_jwt(token)
        uid = str((p or {}).get("user_id") or "").strip()
        if uid:
            return uid
    except Exception as _e:
        logger.warning("owner_guard：auth_middleware 验败：%s: %s", type(_e).__name__, _e)
    try:
        from core.lib.auth_api import auth_manager as _am
        p = _am.verify_token(token)
        uid = str((p or {}).get("user_id") or "").strip()
        if uid:
            return uid
    except Exception as _e:
        logger.warning("owner_guard：auth_api 验败：%s: %s", type(_e).__name__, _e)
    return ""


def owner_ok(req):
    """True ＝ 有合法 owner（本机 ／ 远端持有效 JWT）；False ⇒ 调用方必 403。"""
    if is_loopback(req):
        return True
    if str(os.environ.get("AUTH_EXTERNAL_REQUIRE", "1")) == "0":
        return True
    return bool(_verify(_bearer(req)))


def deny(reason):
    return jsonify({"ok": False, "error": str(reason)[:300], "code": "owner_required"}), 403


def install(bp):
    """把闸装到**同一蓝图**（一处）：45 条写路由动态全覆盖（含后加之路由）。"""
    @bp.before_request
    def _owner_gate():
        if request.method not in WRITE_METHODS:
            return None
        if owner_ok(request):
            return None
        return deny("此写路由须 owner：本机环回，或远端有效 JWT（来源 %s）"
                    % (request.remote_addr or "?"))
    return bp
