# -*- coding: utf-8 -*-
"""浏览器治理/状态路由（P1 拆出，Blueprint）—— 薄包装 → core.lib.v8.browser_local"""
from flask import Blueprint, jsonify, request

bp = Blueprint("browser", __name__)


@bp.route("/v9/browser/publish_history", methods=["GET"])
def v9_browser_publish_history():
    _ph = request.args or {}
    _ph_uid = _ph.get("user_id", "default")
    _ph_limit = int(_ph.get("limit", 20) or 20)
    try:
        from core.lib.v8.browser_local import list_publish_history

        return jsonify({"success": True, "publish_history": list_publish_history(_ph_uid, limit=_ph_limit)})
    except Exception as _ph_err:
        return jsonify({"success": False, "error": str(_ph_err)[:300]})


@bp.route("/v9/browser/monitor", methods=["GET"])
def v9_browser_monitor():
    _bm = request.args or {}
    _bm_uid = _bm.get("user_id", "default")
    try:
        from core.lib.v8.browser_local import list_monitor_jobs, list_reply_history, list_reply_queue

        return jsonify(
            {
                "success": True,
                "monitors": list_monitor_jobs(_bm_uid),
                "reply_queue": list_reply_queue(_bm_uid, status=_bm.get("status", "") or ""),
                "reply_history": list_reply_history(_bm_uid, limit=20),
            }
        )
    except Exception as _bm_err:
        return jsonify({"success": False, "error": str(_bm_err)[:300]})


@bp.route("/v9/browser/gate", methods=["GET"])
def v9_browser_gate():
    from core.lib.v8.browser_local import session_gate

    return jsonify({"success": True, "gate": session_gate(request.args.get("user_id", ""))})


@bp.route("/v9/browser/grant", methods=["POST"])
def v9_browser_grant():
    from core.lib.v8.browser_local import grant_browser_session

    d = request.json or {}
    r = grant_browser_session(
        d.get("user_id", ""),
        hosts=d.get("hosts"),
        actions=d.get("actions"),
        ttl_s=int(d.get("ttl_s") or 1800),
        note=d.get("note", "老板授权"),
    )
    return jsonify(r)


@bp.route("/v9/browser/stop", methods=["POST"])
def v9_browser_stop():
    from core.lib.v8.browser_local import stop_browser_session

    d = request.json or {}
    return jsonify(stop_browser_session(d.get("user_id", ""), d.get("reason", "老板手动停止")))


@bp.route("/v9/browser/resume", methods=["POST"])
def v9_browser_resume():
    from core.lib.v8.browser_local import resume_browser_session

    d = request.json or {}
    return jsonify(resume_browser_session(d.get("user_id", "")))


@bp.route("/v9/browser/revoke", methods=["POST"])
def v9_browser_revoke():
    from core.lib.v8.browser_local import revoke_browser_session

    d = request.json or {}
    return jsonify(revoke_browser_session(d.get("user_id", "")))


@bp.route("/v9/browser/status", methods=["GET"])
def v9_browser_status():
    _bs = request.args or {}
    _bs_uid = _bs.get("user_id", "default")
    try:
        from core.lib.v8.browser_local import get_connection_info

        return jsonify({"success": True, **get_connection_info(_bs_uid)})
    except Exception as _bs_err:
        return jsonify({"success": False, "error": str(_bs_err)[:200]})
