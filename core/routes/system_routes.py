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
    # ⭐ pm_1616 令一：起服「准备中」之可读读数（一处定形 · core/gateway/boot_progress.py）——
    #   门开即可答（本端唯读内存之态 · ⛔ 等重初始化之毕）。
    try:
        from core.gateway.boot_progress import boot_progress
        _boot = boot_progress.snapshot()
    except Exception as _e_boot:
        _boot = {"state": "unknown", "note": "读数⛔ 得：%s" % str(_e_boot)[:120]}
    # ⭐ pm_1628 §二.2 令二：版本元数据（装根 `version.json`）之读数 ——
    #   ⚠ 缺件 ⁄ 坏 ⇒ 照实报（available=False ＋ 因）（⛔ 静默 · 承「真读数」）。
    try:
        from core.lib import build_info as _bi
        _build = _bi.report()
    except Exception as _e_build:                              # noqa: BLE001 — 照实报因
        _build = {"available": False, "note": "读数⛔ 得：%s" % str(_e_build)[:120]}
    # ⭐ pm_1640 §一.2 之律（**读一处（/health）· 动分端（/v9/pa/*）**）：面之读数唯此端 ⇒
    #   落点声明（留言板）亦在此（形唯自 `feedback_target.face()` 一处出 · ⛔ 二处各写）。
    #   ⚠ 将来「更新之读数」（有新版 ／ 已是最新 ／ 大小 ／ 通道）⇒ 俟甲-P0 ⇒ 落 `update` 键（⛔ 新端）。
    try:
        from core.lib import feedback_target as _ft
        _feedback = _ft.face()
    except Exception as _e_fb:                                 # noqa: BLE001 — 照实报因
        _feedback = {"mode": None, "outbound": None, "note": "读数⛔ 得：%s" % str(_e_fb)[:120]}
    return jsonify({
        "status": "healthy" if startup_manager.ready else "starting",
        "version": __version__,
        "build": _build,
        "feedback": _feedback,
        "startup": startup_manager.status(),
        "hardware": hardware_probe.report(),
        "boot": _boot,
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
