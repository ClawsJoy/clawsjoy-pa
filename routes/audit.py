# -*- coding: utf-8 -*-
"""审计/越权记录路由（P1 拆出，Blueprint）—— 薄包装 → core.gateway.audit / core.lib.gateway_helpers"""

from flask import Blueprint, jsonify, request

from core.lib.gateway_helpers import read_agent_state

bp = Blueprint("audit_routes", __name__)


@bp.route("/v9/audit/escalations", methods=["GET"])
def v9_audit_escalations():
    """越权拦截记录: GET /v9/audit/escalations?user_id=xx&session_id=xx

    返回 [{timestamp, tool, target, reason, action}] 按时间倒序。
    """
    _q = request.args or {}
    _uid = _q.get("user_id", "default")
    _sid = _q.get("session_id", "")
    if not _sid:
        return jsonify({"success": False, "error": "session_id 必填"})
    try:
        _st = read_agent_state(_uid, _sid)
        _rows = _st.get("escalations") or []
        if not isinstance(_rows, list):
            _rows = []
        _rows = sorted(_rows, key=lambda r: str(r.get("timestamp", "")), reverse=True)
        return jsonify({"success": True, "escalations": _rows})
    except Exception as _ae_err:
        return jsonify({"success": False, "error": str(_ae_err)[:300]})


@bp.route("/v9/audit/tool_flow", methods=["GET"])
def v9_audit_tool_flow():
    """工具执行流: GET /v9/audit/tool_flow?session_id=xx[&limit=N]

    返回 [{ts, tool, success, error, elapsed_ms, round}] 按时间倒序(读 audit jsonl)。
    """
    _q = request.args or {}
    _sid = _q.get("session_id", "")
    if not _sid:
        return jsonify({"success": False, "error": "session_id 必填"})
    try:
        from core.gateway.audit import read_audit_records

        _limit = int(_q.get("limit") or 200)
        _recs = read_audit_records(session_id=_sid, limit=_limit)
        _rows = [
            {
                "ts": r.get("ts", 0),
                "ts_iso": r.get("ts_iso", ""),
                "tool": r.get("tool", ""),
                "success": r.get("success", False),
                "elapsed_ms": r.get("elapsed_ms", 0),
                "round": r.get("round", 0),
            }
            for r in _recs
        ]
        _rows.sort(key=lambda r: r.get("ts", 0), reverse=True)
        return jsonify({"success": True, "tool_flow": _rows})
    except Exception as _tf_err:
        return jsonify({"success": False, "error": str(_tf_err)[:300]})


@bp.route("/v9/audit/approvals", methods=["GET"])
def v9_audit_approvals():
    """审批记录: GET /v9/audit/approvals?user_id=xx&session_id=xx
    返回 [{timestamp, kind(write|plan), action(approved|rejected), target, detail}] 按时间倒序。"""
    # #15 P0: 查询前触发 pending TTL 清理(防过期 pending 堆积)
    try:
        from core.gateway.write_gate import _pending_cleanup

        _pending_cleanup()
    except Exception:
        pass
    _q = request.args or {}
    _uid = _q.get("user_id", "default")
    _sid = _q.get("session_id", "")
    if not _sid:
        return jsonify({"success": False, "error": "session_id 必填"})
    try:
        _st = read_agent_state(_uid, _sid)
        _rows = _st.get("approvals") or []
        if not isinstance(_rows, list):
            _rows = []
        _rows = sorted(_rows, key=lambda r: str(r.get("timestamp", "")), reverse=True)
        return jsonify({"success": True, "approvals": _rows})
    except Exception as _ap_err:
        return jsonify({"success": False, "error": str(_ap_err)[:300]})


@bp.route("/v9/auto_fixes", methods=["GET"])
def v9_auto_fixes():
    """查询待审核的自动修复建议"""
    try:
        from core.lib.code_entity_extractor import extractor

        return jsonify({"success": True, "auto_fixes": extractor.list_pending_auto_fixes()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@bp.route("/v9/auto_fixes/approve", methods=["POST"])
def v9_auto_fixes_approve():
    """审核通过：将 auto_fix_suggestion 标记为 approved"""
    try:
        data = request.get_json(force=True)
        entity_name = data.get("name")
        if not entity_name:
            return jsonify({"success": False, "error": "缺少 id 参数"}), 400
        from core.lib.code_entity_extractor import extractor

        extractor.set_auto_fix_status(entity_name, "approved")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@bp.route("/v9/auto_fixes/reject", methods=["POST"])
def v9_auto_fixes_reject():
    """审核拒绝：将 auto_fix_suggestion 标记为 rejected"""
    try:
        data = request.get_json(force=True)
        entity_name = data.get("name")
        if not entity_name:
            return jsonify({"success": False, "error": "缺少 id 参数"}), 400
        from core.lib.code_entity_extractor import extractor

        extractor.set_auto_fix_status(entity_name, "rejected")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
