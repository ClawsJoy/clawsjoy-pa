# -*- coding: utf-8 -*-
"""/v9/agent/chat 薄路由（P3-B 迁出主文件，2026-09-12）。

编排下沉 core/gateway/v9_chat/entry.py::run_chat_entry；本文件只做注入注册 + 响应包装。
"""
from flask import Blueprint, Response, jsonify, request, stream_with_context

bp = Blueprint("v9_chat_routes", __name__)
_deps = {}


def register(app, *, bridge_loop_fn, allowed_commands, max_context_tokens, deepseek_key_loaded, resolve_session_id_fn):
    """注入 main 内部依赖后注册路由（防循环 import）。"""
    _deps.update(
        bridge_loop_fn=bridge_loop_fn,
        allowed_commands=allowed_commands,
        max_context_tokens=max_context_tokens,
        deepseek_key_loaded=deepseek_key_loaded,
        resolve_session_id_fn=resolve_session_id_fn,
    )
    app.add_url_rule("/v9/agent/chat", view_func=v9_agent_chat, methods=["POST"], endpoint="v9_agent_chat")


def v9_agent_chat():
    """代理 DeepSeek API 调用，前端不暴露 Key"""
    from core.gateway.v9_chat.entry import run_chat_entry

    payload, kind = run_chat_entry(data=request.json or {}, deps=_deps)
    if kind == "stream":
        return Response(stream_with_context(payload), mimetype="text/event-stream")
    return jsonify(payload)
