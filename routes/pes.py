# -*- coding: utf-8 -*-
"""V9-PES 只读投影路由（M2-A · Step 1）—— 薄包装 → :mod:`core.pa.pes_projection`。

先例：``routes/audit.py``（同样是薄路由）。
**本模块不读写任何状态文件**，全部事实由投影层只读取得。
"""

from flask import Blueprint, jsonify, request

from core.pa.pes_projection import DEFAULT_LIMIT, project_runs

bp = Blueprint("pes_routes", __name__)


@bp.route("/v9/pes/runs", methods=["GET"])
def v9_pes_runs():
    """只读运行投影: GET /v9/pes/runs?user_id=xx&session_id=xx&limit=N

    返回 ``{success, generated_at, runs[], degradations[]}``；
    **空库返回空数组 + degradations，不 500**。
    """
    _q = request.args or {}
    try:
        _limit = int(_q.get("limit") or DEFAULT_LIMIT)
    except Exception:
        _limit = DEFAULT_LIMIT
    try:
        return jsonify(project_runs(user_id=_q.get("user_id") or None,
                                    session_id=_q.get("session_id") or None,
                                    limit=_limit))
    except Exception as _e:
        return jsonify({"success": False, "error": str(_e)[:300]})
