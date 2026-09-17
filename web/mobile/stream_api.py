#!/usr/bin/env python3
"""Stream Api - Stream Api 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
import time

from flask import Blueprint, Response, jsonify, request

from core.agents.builtin.orchestrator import OrchestratorAgent

stream_bp = Blueprint("stream", __name__, url_prefix="/api/stream")


@stream_bp.route("/chat")
def stream_chat():
    """SSE 流式响应"""
    message = request.args.get("message", "")
    user_id = request.args.get("user_id", "mobile_user")

    def generate():
        orch = OrchestratorAgent(user_id)

        # 流式生成（模拟，实际可接入 LLM 流式）
        result = orch.auto_dispatch(message)
        response = result.get("result", {}).get("response", "处理完成")

        # 逐字发送
        for char in response:
            yield f"data: {json.dumps({'content': char, 'done': False})}\n\n"
            time.sleep(0.03)  # 模拟流式效果

        yield f"data: {json.dumps({'done': True})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@stream_bp.route("/voice", methods=["POST"])
def voice_input():
    """语音输入接口"""
    # 接收音频数据
    audio_data = request.data
    # TODO: 调用 ASR 服务
    # 这里返回模拟结果
    return jsonify({"text": "用户语音输入的内容", "success": True})
