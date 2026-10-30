# -*- coding: utf-8 -*-
"""静态文件 / 前端页面路由（P1 拆出，Blueprint）"""

import sys
_PY = sys.executable or "python3"  # Windows(2026-09-17): 本机无 python3, 用当前解释器
import os

from flask import Blueprint, current_app, jsonify, send_from_directory

from core.gateway import _proc as _proc  # ⭐ 子进程唯一出口（窗隐）

# ⭐ 版号之「一处定形」（承 pm_1384 §三.5）—— ⛔ 本档再书字面（旧字面 ⇒ 拔）
from core.lib.version import SERVICE_NAME, __version__

bp = Blueprint("static_routes", __name__)


@bp.route("/web/<path:filename>")
def serve_web(filename):
    """静态件。**真源**：本 bp 在 ``agent_gateway_enhanced.py:385`` import / ``:392`` register。

    PM-011（2026-09-30 · PM 批）：`/web/pa.html` 额外做两件 ——
      ① **no-store**：每次拿到的都必须是现盘那份。本轮「😵 服务暂不可用」的归属之争
         根因就是「两版页面无法区分」（PM 把旧气泡重绘读成现役行为）；
      ② 响应头带 **服务端现算的构建指纹** `X-PA-Build-Sha16` ⇒ 探针/CDP **不必执行 JS**
         就能认版本（页面内徽标 `#paBuild` 是给人看的，见 `core/pa/gateway_routes.py:/v9/pa/build`）。
      读不到就写 `unreadable` —— ⛔ 不填占位符假装有读数（与「0 看起来像读数」同族）。

    ⚠ 自陈（2026-09-30）：本段我**第一版写进了 `core/web/health.py`** —— 那个 `health_bp`
      全仓 **0 处注册**（死码）⇒ 线上**毫无变化**，而我的单测却是绿的（判据打在死模块上＝假绿）。
      抓出来的是**现场复核**（响应头没有指纹），⛔ 不是测试。⇒ 判据必须打在**真源**上，
      并留 `tests/unit/test_pm011_pa_build_stamp.py::test_t6` 把真源钉死。
    """
    resp = send_from_directory("web", filename)
    if filename == "pa.html":
        resp.headers["Cache-Control"] = "no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        try:
            import hashlib as _hl

            with open(os.path.join(current_app.root_path, "web", "pa.html"), "rb") as _f:
                resp.headers["X-PA-Build-Sha16"] = _hl.sha256(_f.read()).hexdigest()[:16]
        except Exception:
            resp.headers["X-PA-Build-Sha16"] = "unreadable"
    return resp



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
    result = _proc.run_hidden([_PY, script], capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
    if result.returncode == 0:
        return {"success": True, "download_url": f"/exports/seedance_{project}.zip"}
    return {"success": False, "error": result.stderr[:200]}


@bp.route("/data/videos/<path:filename>")
def serve_video(filename):
    return send_from_directory("data/videos", filename)


@bp.route("/favicon.ico")
def favicon():
    return send_from_directory("web", "favicon.ico")


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
    return jsonify({"service": SERVICE_NAME, "version": __version__})
