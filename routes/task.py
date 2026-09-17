# -*- coding: utf-8 -*-
"""任务状态路由（P3-A 拆出，Blueprint）—— v9 task save_progress/set_mode/status"""

import json
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request

from core.gateway.shared_state import _PROJECT_ROOT, _resolve_v9_session_id
from core.gateway.state_persist import _safe_serialize_state

bp = Blueprint("task_routes", __name__)


@bp.route("/v9/task/save_progress", methods=["POST"])
def v9_save_task_progress():
    """保存任务中断进度到 .agent_state.json"""
    data = request.json or {}
    user_id = data.get("user_id", "default")
    session_id, _auto_sid = _resolve_v9_session_id(user_id, data.get("session_id", "default"))
    progress = data.get("progress", {})

    state_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
    try:
        state = json.loads(state_file.read_text())
    except Exception:
        state = {} if state_file.exists() else {}

    state["task_progress"] = {
        "status": "paused",
        "original_task": progress.get("original_task", ""),
        "completed_steps": progress.get("completed_steps", []),
        "pending_steps": progress.get("pending_steps", []),
        "total_rounds": progress.get("total_rounds", 0),
        "paused_at": datetime.now().isoformat(),
    }
    state_file.write_text(_safe_serialize_state(state))
    return jsonify({"ok": True})


@bp.route("/v9/task/set_mode", methods=["POST"])
def v9_task_set_mode():
    """设置任务执行模式（auto/semi/manual）"""
    data = request.json or {}
    mode = data.get("mode", "auto")
    user_id = data.get("user_id", "default")
    if mode not in ("auto", "semi", "manual"):
        return jsonify({"ok": False, "error": f"非法 mode: {mode}，可选: auto/semi/manual"}), 400
    mode_file = Path(_PROJECT_ROOT) / "data" / "v8" / "task_mode.json"
    try:
        mode_file.parent.mkdir(parents=True, exist_ok=True)
        mode_data = {}
        if mode_file.exists():
            try:
                mode_data = json.loads(mode_file.read_text())
            except Exception:
                mode_data = {}
        mode_data[user_id] = {"mode": mode, "updated_at": datetime.now().isoformat()}
        mode_file.write_text(json.dumps(mode_data, ensure_ascii=False, indent=2))
        return jsonify({"ok": True, "mode": mode, "user_id": user_id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/v9/task/status", methods=["GET"])
def v9_task_status():
    import json as _json

    user_id = request.args.get("user_id", "default")
    session_id, _auto_sid = _resolve_v9_session_id(user_id, request.args.get("session_id", "default"))

    async_state_file = Path(f"data/projects/{user_id}/{session_id}/.task_state.json")
    if async_state_file.exists():
        async_state = _json.loads(async_state_file.read_text())
        return jsonify({"success": True, "status": async_state.get("status", "running"), "async_task": async_state})

    state_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
    if state_file.exists():
        state = _json.loads(state_file.read_text())
        tp = state.get("task_progress", {})
        if isinstance(tp, str):
            try:
                tp = _json.loads(tp) if tp.strip().startswith("{") else {"last_action": tp}
            except Exception:
                tp = {"last_action": tp}
        return jsonify({"success": True, "status": tp.get("last_action", "running"), "task_progress": tp})
    return jsonify({"success": True, "status": "not_found"})
