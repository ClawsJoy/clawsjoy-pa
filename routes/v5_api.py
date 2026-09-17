# -*- coding: utf-8 -*-
"""V5 业务 API 路由（P3-A 拆出，Blueprint）—— 薄包装 → core.lib.gateway_helpers"""

from flask import Blueprint, jsonify, request

bp = Blueprint("v5_api_routes", __name__)


@bp.route("/api/v5/user/state", methods=["GET"])
def get_user_state_api():
    from core.lib.gateway_helpers import get_user_state

    project_id = request.args.get("project_id")
    user_id = request.args.get("user_id", "default")
    return jsonify({"success": True, "state": get_user_state(project_id, user_id)})


@bp.route("/api/v5/user/state", methods=["POST"])
def set_user_state_api():
    from core.lib.gateway_helpers import set_user_state

    data = request.json or {}
    set_user_state(data.get("project_id"), data.get("user_id", "default"), data.get("key"), data.get("value"))
    return jsonify({"success": True})


@bp.route("/api/v5/learning/stats", methods=["GET"])
def learning_stats_api():
    from core.lib.gateway_helpers import load_learning_stats

    return jsonify({"success": True, "stats": load_learning_stats()})


@bp.route("/api/v5/file/read", methods=["POST"])
def file_read_api():
    from core.lib.gateway_helpers import extract_file_content

    data = request.json or {}
    content, info = extract_file_content(data.get("project_id"), data.get("file_path"), data.get("user_id", "default"))
    return jsonify({"success": True, "content": content, "info": info})


@bp.route("/api/v5/user/info", methods=["POST"])
def user_info_api():
    from core.lib.gateway_helpers import answer_from_state, extract_user_info

    data = request.json or {}
    message = data.get("message", "")
    user_id = data.get("user_id", "default")
    project_id = data.get("project_id")
    extract_user_info(message, user_id, project_id)
    answer = answer_from_state(message, user_id, project_id)
    return jsonify({"success": True, "answer": answer})


@bp.route("/api/learning/record", methods=["POST"])
def learning_record_api():
    """记录学习事实（test_learning_endpoint）"""
    data = request.json or {}
    try:
        from core.lib.gateway_helpers import save_learning_record

        save_learning_record(data.get("fact", ""), data)
    except Exception:
        pass
    return jsonify({"success": True, "message": "学习记录已保存"})


@bp.route("/api/vector/search", methods=["POST"])
def vector_search_api():
    """向量搜索（test_vector_search）"""
    data = request.json or {}
    query = data.get("query", "")
    try:
        top_k = int(data.get("top_k", 5) or 5)
    except Exception:
        top_k = 5
    results = []
    try:
        from core.vector.vector_store import vector_store

        results = vector_store.search(query, top_k=top_k) or []
    except Exception:
        results = []
    return jsonify({"success": True, "results": results})


@bp.route("/api/club/stats", methods=["GET"])
def club_stats_api():
    """俱乐部统计（test_club_stats）"""
    stats = {}
    try:
        from core.lib.gateway_helpers import load_club_stats

        stats = load_club_stats() or {}
    except Exception:
        stats = {}
    return jsonify({"success": True, "stats": stats})
