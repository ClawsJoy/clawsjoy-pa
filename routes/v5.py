# -*- coding: utf-8 -*-
"""v5 执行入口路由（P3-A 拆出，Blueprint）—— 薄包装 → core.gateway.v5_execute / chat_stream"""

from flask import Blueprint, jsonify, request

bp = Blueprint("v5_routes", __name__)


@bp.route("/v5/execute", methods=["POST"])
@bp.route("/api/v5/execute", methods=["POST"])
def v5_execute():
    from core.gateway.v5_execute import v5_execute_handler

    return v5_execute_handler()


@bp.route("/api/v5/wisdom/chat", methods=["POST"])
def wisdom_chat():
    """兼容旧入口 → 转发到 /v5/execute"""
    return v5_execute()


@bp.route("/api/v5/enhanced/chat", methods=["POST"])
def enhanced_chat():
    """[兼容旧版] 转发到统一入口"""
    return v5_execute()


@bp.route("/api/agent/<agent_name>/message", methods=["POST"])
def agent_message(agent_name):
    """[兼容旧版] 旧Agent直调 → 转发到统一入口"""
    return v5_execute()


@bp.route("/api/v5/chat/stream", methods=["POST"])
def chat_stream():
    from core.gateway.chat_stream import chat_stream_handler

    return chat_stream_handler()
