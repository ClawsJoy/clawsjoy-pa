#!/usr/bin/env python3
"""Api - Api 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from flask import Blueprint, jsonify, request

from core.agents.builtin.orchestrator import OrchestratorAgent

mobile_bp = Blueprint("mobile", __name__, url_prefix="/api/mobile")


@mobile_bp.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "")
    user_id = data.get("user_id", "mobile_user")

    orch = OrchestratorAgent(user_id)
    result = orch.auto_dispatch(message)

    return jsonify(
        {
            "success": True,
            "response": result.get("result", {}).get("response", "处理完成"),
        }
    )


@mobile_bp.route("/sync", methods=["POST"])
def sync():
    """同步本地数据到云端（脱敏）"""
    data = request.json
    # 只接收脱敏统计，不接收隐私
    stats = data.get("stats", {})
    # TODO: 存储到俱乐部统计
    return jsonify({"success": True})
