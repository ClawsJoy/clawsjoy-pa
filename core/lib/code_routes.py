#!/usr/bin/env python3
"""Code Routes - Code Routes 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""CODE Agent 路由 - 配置驱动"""

from flask import jsonify, request

from core.lib.code_generator import code_generator


def register_code_routes(app):
    """注册 CODE Agent 路由"""

    @app.route("/api/code/generate", methods=["POST"])
    def api_code_generate():
        data = request.json
        result = code_generator.generate(
            request=data.get("request", ""), user_id=data.get("user_id", "default")
        )
        return jsonify(result)

    @app.route("/api/code/modify", methods=["POST"])
    def api_code_modify():
        data = request.json
        result = code_generator.modify(
            code=data.get("code", ""), instruction=data.get("instruction", "")
        )
        return jsonify(result)

    @app.route("/api/code/feedback", methods=["POST"])
    def api_code_feedback():
        data = request.json
        result = code_generator.record_feedback(
            user_id=data.get("user_id", "default"),
            feedback=data.get("feedback", ""),
            accepted=data.get("accepted", False),
        )
        return jsonify(result)

    @app.route("/api/code/status", methods=["GET"])
    def api_code_status():
        return jsonify(
            {"status": "online", "generator": "code_generator", "config_driven": True}
        )

    print("✅ CODE Agent 路由已注册 (配置驱动)")
