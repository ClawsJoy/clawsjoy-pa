# -*- coding: utf-8 -*-
"""指标/抓取路由（P3-A 拆出，Blueprint）—— tool_flow 指标 + 链接抓全文"""

from flask import Blueprint, jsonify, request

bp = Blueprint("metrics_routes", __name__)


@bp.route("/v9/metrics/tool_flow", methods=["GET"])
def v9_metrics_tool_flow():
    _mf = request.args or {}
    _mf_hours = int(_mf.get("hours", 24) or 24)
    try:
        from core.context.context_manager import tool_flow_stats

        _st = tool_flow_stats(window_hours=_mf_hours)
        _tool = _mf.get("tool")
        _task = _mf.get("task")
        if _tool:
            _st = {**_st, "by_tool": {_tool: _st["by_tool"].get(_tool, {})}}
        if _task:
            _st = {**_st, "by_task": {_task: _st["by_task"].get(_task, {})}}
        return jsonify({"success": True, "stats": _st})
    except Exception as _mf_err:
        return jsonify({"success": False, "error": str(_mf_err)[:300]})


def _infer_title_from_url(url):
    """从 URL 推断页面标题(主机名 + 路径尾段, 无网络请求)。"""
    try:
        from urllib.parse import urlparse as _up_par

        _p = _up_par(url)
        _host = (_p.hostname or "page").replace("www.", "")
        _tail = _p.path.rstrip("/").split("/")[-1] if _p.path.rstrip("/") else ""
        _tail = _tail.split(".")[0] if _tail else ""
        if _tail and _tail != _host and len(_tail) <= 40:
            return f"{_tail} · {_host}"
        return _host
    except Exception:
        return "页面"


@bp.route("/v9/fetch", methods=["GET"])
def v9_fetch():
    _url = (request.args or {}).get("url", "").strip()
    if not _url:
        return jsonify({"success": False, "error": "url 必填"})
    try:
        from core.tools.fetch_web import FetchWebPlugin

        _r = FetchWebPlugin().execute({"url": _url}, object())
        if not _r.get("success"):
            return jsonify({"success": False, "error": str(_r.get("error", "抓取失败"))[:300]})
        return jsonify(
            {
                "success": True,
                "content": str(_r.get("content", "")),
                "url": str(_r.get("url") or _url),
                "title": _infer_title_from_url(str(_r.get("url") or _url)),
                "truncated": bool(_r.get("truncated")),
                "length": int(_r.get("length", 0)),
            }
        )
    except Exception as _f_err:
        return jsonify({"success": False, "error": str(_f_err)[:300]})
