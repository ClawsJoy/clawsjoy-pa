"""系统级路由模块：健康检查与系统状态

将网关 agent_gateway_enhanced.py 中的系统级路由提取为独立 Blueprint：
- GET /health                   健康检查
- GET /api/v5/health/detailed   详细健康检查
- GET /metrics                  系统指标

依赖（startup_manager / hardware_probe / health_checker）均为 core.lib 单例，
通过路由函数内惰性导入获取，保证模块独立可加载、可单测。
"""

from flask import Blueprint, Response, jsonify, request

# ⭐ 版号之「一处定形」（承 pm_1384 §三.5）—— ⛔ 本档再书字面（旧字面 ⇒ 拔）
from core.lib.version import __version__

try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
except ImportError:  # pragma: no cover
    CONTENT_TYPE_LATEST = "text/plain"

    def generate_latest():
        return b""

system_bp = Blueprint("system", __name__)


@system_bp.route("/health", methods=["GET"])
def health():
    from core.lib.startup import startup_manager
    from core.lib.hardware_probe import hardware_probe
    return jsonify({
        "status": "healthy" if startup_manager.ready else "starting",
        "version": __version__,
        "startup": startup_manager.status(),
        "hardware": hardware_probe.report(),
    })


@system_bp.route("/api/v5/health/detailed", methods=["GET"])
def detailed_health():
    from core.lib.health_check import health_checker
    return jsonify(health_checker.check_all())


@system_bp.route("/metrics", methods=["GET"])
def metrics():
    if "prometheus" in request.headers.get("Accept", ""):
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
    import psutil
    return jsonify({
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent,
        },
        "status": "ok",
    })
