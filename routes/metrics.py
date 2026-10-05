# -*- coding: utf-8 -*-
"""指标/抓取路由（P3-A 拆出，Blueprint）—— tool_flow 指标 + 链接抓全文"""

from flask import Blueprint, jsonify, request

bp = Blueprint("metrics_routes", __name__)


def _missing(_key):
    """必填缺失 ⇒ 400 ＋ 定位（PM-011 N11：同一键 ⛔ 不许两套码；形制 `<路由>: 缺 <键>`）。

    ⭐ T2-刀8 §三（2026-10-05 · PM 裁「准办」）：**只增** `missing` ＋ `kind` 两键 ——
      由：面之「**0 件**」与「**缺参 400**」同形而 ⛔ 可辨 ⇒ 读者误把错渲染成空（承「空 ⛔ 混 缺」）。
      ⛔ 破既有 `400` 之形（`success:false` ＋ `error` 逐字保 · 承裁「只增键」）。
    """
    _rule = request.url_rule
    _rt = (_rule.rule if _rule is not None else "?").lstrip("/")
    return jsonify({"success": False, "error": "%s: 缺 %s" % (_rt, _key),
                    "missing": [_key], "kind": "missing_param", "route": _rt}), 400


@bp.route("/v9/metrics/tool_flow", methods=["GET"])
def v9_metrics_tool_flow():
    _mf = request.args or {}
    _mf_hours = int(_mf.get("hours", 24) or 24)
    try:
        from core.context.context_manager import tool_flow_stats

        _st = tool_flow_stats(window_hours=_mf_hours)
        # ⭐ T2-刀9 §二（2026-10-05 · PM 裁「准你办」）：**面之域**的自陈
        #   病：面名「工具流」而唯覆**过网关工具路**者 ⇒ 各席自有之 exec ⛔ 入账
        #        而面⛔ 声明 ⇒ 读者以为「本线无作业」（假空）。今**显式标其域**。
        _st["coverage"] = {
            "面之径逐字": "data/v8/tool_metrics.jsonl",
            "写者": "core/context/context_manager.py:record_tool_flow",
            "调用点": ["core/gateway/tool_router.py", "core/gateway/sandbox_ops.py",
                      "core/gateway/guards/registry.py:AuditGuard"],
            "sessions_seen": sorted(_st.get("by_task", {}).keys()),
            "不入账": ("各席**自有之 exec**（如 `f202f89` 之 T2-刀线工）⛔ 过网关工具路 "
                        "⇒ 不入本账；它们在 `data/v9/pa/dispatch.jsonl`（派件）与各牌账里"),
            "注": "本面 **⛔ 充全量台账**（承「面须钉」）；新知之路须显式入 `调用点` 方可入账",
        }
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
        return _missing("url")
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
