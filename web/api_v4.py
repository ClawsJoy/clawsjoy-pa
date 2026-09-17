#!/usr/bin/env python3
"""Api V4 - Api V4 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from flask import Blueprint, jsonify, request

from intelligence.service_v4 import intelligence_service
from lib.success_predictor import success_predictor

api_bp = Blueprint("api_v4", __name__, url_prefix="/api/v4")


@api_bp.route("/status")
def get_status():
    """系统状态"""
    return jsonify(
        {
            "version": "4.0.0",
            "service": intelligence_service.get_status(),
            "predictor": success_predictor.get_stats() if success_predictor else {},
        }
    )


@api_bp.route("/predict/<task_name>")
def predict(task_name):
    """预测任务"""
    return jsonify(intelligence_service.predict(task_name))


@api_bp.route("/decide", methods=["POST"])
def decide():
    """决策"""
    context = request.json or {}
    return jsonify(intelligence_service.decide(context))


@api_bp.route("/analyze/<task_name>")
def analyze(task_name):
    """综合分析"""
    return jsonify(intelligence_service.analyze_task(task_name))


@api_bp.route("/health")
def health():
    """健康检查"""
    return jsonify({"status": "ok", "version": "4.0.0"})


# 兼容旧版本 API
@api_bp.route("/v3/status")
def v3_status():
    """v3 兼容接口"""
    return jsonify({"version": "3.2.0", "compatible": True})

@api_bp.route("/export/comic/<project>")
def export_comic(project):
    """导出漫剧素材包"""
    import subprocess, os
    script = "scripts/export_for_seedance.py"
    if not os.path.exists(script):
        return {"success": False, "error": "导出脚本不存在"}
    
    result = subprocess.run(["python3", script], capture_output=True, text=True)
    if result.returncode == 0:
        return {
            "success": True,
            "download_url": f"/exports/seedance_{project}.zip",
            "message": "导出成功"
        }
    return {"success": False, "error": result.stderr}
