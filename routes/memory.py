# -*- coding: utf-8 -*-
"""记忆路由（P3-A 拆出，Blueprint）—— 薄包装 → agent_cortex / gateway_helpers.save_memory"""

from flask import Blueprint, jsonify, request

bp = Blueprint("memory_routes", __name__)


@bp.route("/api/v5/memory/remember", methods=["POST"])
def memory_remember():
    data = request.json or {}
    user_id = data.get("user_id", "guest")
    fact = data.get("fact", "")
    from core.agents.cortex import agent_cortex
    from core.lib.gateway_helpers import save_memory

    result = agent_cortex.process(f"记住 {fact}", user_id)
    if result.get("success"):
        return jsonify({"success": True, "message": "记忆已存储"})
    save_memory(user_id, fact)
    return jsonify({"success": True, "message": "记忆已存储"})


@bp.route("/api/v5/memory/recall", methods=["POST"])
def memory_recall():
    data = request.json or {}
    user_id = data.get("user_id", "guest")
    query = data.get("query", "")
    from core.agents.cortex import agent_cortex

    result = agent_cortex.process(f"回忆 {query}", user_id)
    return jsonify({"success": True, "results": [result.get("response", "")]})


@bp.route("/api/v5/memory/stats", methods=["GET"])
def memory_stats():
    user_id = request.args.get("user_id", "guest")
    from core.agents.cortex import agent_cortex

    result = agent_cortex.process("列出所有记忆", user_id)
    return jsonify({"success": True, "total": len(result.get("response", ""))})
