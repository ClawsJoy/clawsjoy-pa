# -*- coding: utf-8 -*-
"""浏览器治理/状态路由（P1 拆出，Blueprint）—— 薄包装 → core.lib.v8.browser_local"""
import functools

from flask import Blueprint, jsonify, request

bp = Blueprint("browser", __name__)


class _BadShape(Exception):
    """载荷形状不合格 ⇒ 由 `_shape_400` 统一转 400（本文件 POST 的**唯一** 400 出口）。"""


def _locator():
    """出错位置：取当前规则（⛔ 不硬编码；同一路由 ⛔ 不许两种风格）。"""
    _rule = request.url_rule
    return (_rule.rule if _rule is not None else "?").lstrip("/")


def _shape_400(_fn):
    """唯一 400 出口：`_BadShape` ⇒ `{"success": false, "error": <调用方可见面>}` ＋ 400。"""

    @functools.wraps(_fn)
    def _wrapped(*_a, **_kw):
        try:
            return _fn(*_a, **_kw)
        except _BadShape as _e:
            return jsonify({"success": False, "error": str(_e)}), 400

    return _wrapped


def _post_body():
    """POST 的 JSON 体 ⇒ `dict`；形状不合 ⇒ `_BadShape`。

    ⛔ 形状不合就报错，**不返回空 dict 之类的默认值冒充调用方意图**
    （空载荷退默认值 ⇒ 下游把默认值读成「调用方说了什么」＝ 假读数）。
    """
    _raw = request.get_data(cache=True)
    _d = request.get_json(silent=True)
    if _d is None:
        raise _BadShape("%s: %s" % (_locator(), "body 不是合法 JSON" if _raw else "body 为空（需要 JSON 对象）"))
    if not isinstance(_d, dict):
        raise _BadShape("%s: body 需要 JSON 对象（拿到 %s）" % (_locator(), type(_d).__name__))
    return _d


def _require_text(_d, _key):
    """必填文本字段 ⇒ 值；缺失 / 空白 ⇒ `_BadShape`（⛔ 不落默认值）。"""
    _v = _d.get(_key)
    if not (isinstance(_v, str) and _v.strip()):
        raise _BadShape("%s: 缺 %s" % (_locator(), _key))
    return _v


@bp.route("/v9/browser/publish_history", methods=["GET"])
def v9_browser_publish_history():
    _ph = request.args or {}
    _ph_uid = _ph.get("user_id", "default")
    _ph_limit = int(_ph.get("limit", 20) or 20)
    try:
        from core.lib.v8.browser_local import list_publish_history

        return jsonify({"success": True, "publish_history": list_publish_history(_ph_uid, limit=_ph_limit)})
    except Exception as _ph_err:
        return jsonify({"success": False, "error": str(_ph_err)[:300]})


@bp.route("/v9/browser/monitor", methods=["GET"])
def v9_browser_monitor():
    _bm = request.args or {}
    _bm_uid = _bm.get("user_id", "default")
    try:
        from core.lib.v8.browser_local import list_monitor_jobs, list_reply_history, list_reply_queue

        return jsonify(
            {
                "success": True,
                "monitors": list_monitor_jobs(_bm_uid),
                "reply_queue": list_reply_queue(_bm_uid, status=_bm.get("status", "") or ""),
                "reply_history": list_reply_history(_bm_uid, limit=20),
            }
        )
    except Exception as _bm_err:
        return jsonify({"success": False, "error": str(_bm_err)[:300]})


@bp.route("/v9/browser/gate", methods=["GET"])
def v9_browser_gate():
    from core.lib.v8.browser_local import session_gate

    return jsonify({"success": True, "gate": session_gate(request.args.get("user_id", ""))})


@bp.route("/v9/browser/grant", methods=["POST"])
@_shape_400
def v9_browser_grant():
    from core.lib.v8.browser_local import grant_browser_session

    d = _post_body()
    return jsonify(
        grant_browser_session(
            _require_text(d, "user_id"),
            hosts=d.get("hosts"),
            actions=d.get("actions"),
            ttl_s=int(d.get("ttl_s") or 1800),
            note=_require_text(d, "note"),
        )
    )


@bp.route("/v9/browser/stop", methods=["POST"])
@_shape_400
def v9_browser_stop():
    """PM-011v17 §二(1) 裁：空载荷 ⇒ 400。

    病灶：`d.get("reason", "老板手动停止")` ⇒ 空载荷也生成一句**像人下过令**的 reason
    ⇒ 台账面被伪造（「老板手动停止」不是中性默认值，是一句诬告）。
    """
    from core.lib.v8.browser_local import stop_browser_session

    d = _post_body()
    return jsonify(stop_browser_session(d.get("user_id", ""), _require_text(d, "reason")))


@bp.route("/v9/browser/resume", methods=["POST"])
@_shape_400
def v9_browser_resume():
    from core.lib.v8.browser_local import resume_browser_session

    d = _post_body()
    return jsonify(resume_browser_session(_require_text(d, "user_id")))


@bp.route("/v9/browser/revoke", methods=["POST"])
@_shape_400
def v9_browser_revoke():
    from core.lib.v8.browser_local import revoke_browser_session

    d = _post_body()
    return jsonify(revoke_browser_session(_require_text(d, "user_id")))


@bp.route("/v9/browser/status", methods=["GET"])
def v9_browser_status():
    _bs = request.args or {}
    _bs_uid = _bs.get("user_id", "default")
    try:
        from core.lib.v8.browser_local import get_connection_info

        return jsonify({"success": True, **get_connection_info(_bs_uid)})
    except Exception as _bs_err:
        return jsonify({"success": False, "error": str(_bs_err)[:200]})
