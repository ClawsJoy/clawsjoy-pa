# -*- coding: utf-8 -*-
# 健康检查与静态页面 Blueprint
# 从 agent_gateway_enhanced.py 迁移 6 个路由：
#   /favicon.ico, /, /web, /web/<path:filename>, /workbench, /dashboard

from flask import Blueprint, jsonify, send_from_directory

health_bp = Blueprint("health", __name__)


@health_bp.route("/favicon.ico")
def favicon():
    """站点图标"""
    return send_from_directory("static", "favicon.ico")


@health_bp.route("/")
def index():
    """首页：服务状态"""
    return jsonify({"service": "ClawsJoy Gateway", "version": "6.0.0"})


@health_bp.route("/web")
def web_index():
    """Web 首页"""
    return send_from_directory("web", "index.html")


@health_bp.route("/web/<path:filename>")
def serve_web(filename):
    """Web 静态文件"""
    return send_from_directory("web", filename)


@health_bp.route("/workbench")
def workbench():
    """工作台页面"""
    return send_from_directory("web/dashboard", "workbench.html")


@health_bp.route("/dashboard")
def dashboard():
    """仪表盘页面"""
    return send_from_directory("web/dashboard", "index.html")
