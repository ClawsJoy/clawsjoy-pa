# -*- coding: utf-8 -*-
"""静态文件 / 前端页面路由（P1 拆出，Blueprint）"""
from flask import Blueprint, jsonify, send_from_directory

bp = Blueprint("static_routes", __name__)


@bp.route("/web/<path:filename>")
def serve_web(filename):
    return send_from_directory("web", filename)


@bp.route("/v5.1")
@bp.route("/v5.1/")
@bp.route("/v5.1/<path:filename>")
def serve_v51(filename="index_root.html"):
    return send_from_directory("web/v5.1", filename)


@bp.route("/exports/<path:filename>")
def serve_exports(filename):
    return send_from_directory("exports", filename)


@bp.route("/api/export/comic/<project>")
def export_comic(project):
    import os
    import subprocess

    script = "scripts/export_for_seedance.py"
    if not os.path.exists(script):
        return {"success": False, "error": "导出脚本不存在"}
    result = subprocess.run(["python3", script], capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        return {"success": True, "download_url": f"/exports/seedance_{project}.zip"}
    return {"success": False, "error": result.stderr[:200]}


@bp.route("/data/videos/<path:filename>")
def serve_video(filename):
    return send_from_directory("data/videos", filename)


@bp.route("/favicon.ico")
def favicon():
    return send_from_directory("static", "favicon.ico")


@bp.route("/workbench")
def workbench():
    return send_from_directory("web/dashboard", "workbench.html")


@bp.route("/dashboard")
def dashboard():
    return send_from_directory("web/dashboard", "index.html")


@bp.route("/web")
def web_index():
    return send_from_directory("web", "index.html")


for panel in [
    "code_agent_panel",
    "writer_panel",
    "director_panel",
    "preview",
    "tab_editor",
    "debug_console",
    "diff_viewer",
    "workflow_panel",
    "butler_3d",
]:
    bp.add_url_rule(
        f"/{panel}.html",
        panel.replace("_panel", "_page") if "panel" in panel else panel,
        lambda p=panel: send_from_directory("templates", f"{p}.html"),
    )


@bp.route("/")
def index():
    return jsonify({"service": "ClawsJoy Gateway", "version": "6.0.0"})
