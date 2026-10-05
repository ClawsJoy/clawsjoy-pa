# -*- coding: utf-8 -*-
r"""PM-011v17 · 三处落件的专属门（CW b2a5182 · 2026-09-30）。

PM 2026-09-30 09:5x 裁（v17 答件）：
  §一 轴 A 全局根因 ⇒ **按「一处根因」修**：`error_handler` 放行 `HTTPException`。
      判据 1：非法 JSON ⇒ **400 ＋ 路由定位**（⛔ 不是裸 400）；
      判据 2（反例门）：真·内部异常 ⇒ **必须仍 500**（⛔ 不许把 500 也放行成 400）。
  §二 两处「默认值冒充调用方意图」⇒ 都是病 ⇒ **空载荷 ⇒ 400**：
      (1) `routes/browser.py` `v9_browser_stop`（`reason` 默认「老板手动停止」＝**台账面伪造**）；
      (2) `core/gateway/sandbox_ops.py` 共享装饰器 `:89` ＋ `list`（默认路径冒充调用方意图）。

⛔ 本件不碰（照实上报）：
  · `sandbox_ops.py` 的 `checkpoint`／`rollback` 两处仍是 `request.json or {}`（**同族 · 未批**）；
  · 65 处候选里其余站点（多数是 `200+notok`，⛔ 非假绿）—— 本件**不并批**。
"""
from __future__ import annotations

import pytest
from flask import Flask, abort, jsonify, request

BAD_JSON = b"{not json"


def _err(r):
    j = r.get_json() or {}
    return j.get("error") or ""


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # ⭐ 沙箱根是**相对路径**（`data/projects/...`）⇒ 换 cwd 即隔离，⛔ 不写生产数据面。
    monkeypatch.chdir(tmp_path)
    app = Flask(__name__)
    app.config["PROPAGATE_EXCEPTIONS"] = False
    from core.lib.error_handler import register_error_handlers

    register_error_handlers(app)

    @app.route("/probe/badjson", methods=["POST"])
    def _probe_badjson():
        data = request.json or {}

        return jsonify({"success": True, "echo": data})

    @app.route("/probe/boom", methods=["POST"])
    def _probe_boom():
        raise ValueError("internal-detail-must-not-leak")

    @app.route("/probe/abort", methods=["POST"])
    def _probe_abort():
        abort(403)

    from routes.browser import bp as _browser_bp
    from routes.sandbox import bp as _sandbox_bp

    app.register_blueprint(_sandbox_bp)
    app.register_blueprint(_browser_bp)

    import core.lib.v8.browser_local as _bl

    monkeypatch.setattr(
        _bl,
        "stop_browser_session",
        lambda uid, reason: {"success": True, "stopped": True, "reason": reason, "user_id": uid},
    )
    return app.test_client()


# ==================== 门 G · 轴 A 全局根因（error_handler） ====================

def test_g1_bad_json_is_400_with_route_locator(client):
    """判据 1：非法 JSON ⇒ 400 ＋ 路由定位（⛔ 不是裸 400，⛔ 不是 500）。"""
    r = client.post("/probe/badjson", data=BAD_JSON, content_type="application/json")
    assert r.status_code == 400, "坏 JSON 须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert "probe/badjson" in e, "须带路由定位：%r" % e
    assert "不是合法 JSON" in e, "须说清「收到的形状」：%r" % e
    assert "ValueError" not in e and "Traceback" not in e, "⛔ 不许含内部实现对内面信息：%r" % e


def test_g2_internal_error_still_500_never_400(client):
    """⭐ 反例门（PM §一 判据 2）：真·内部异常 ⇒ **必须仍 500**，⛔ 不许被一起放行成 400。"""
    r = client.post("/probe/boom", data=b"{}", content_type="application/json")
    assert r.status_code == 500, "内部异常须 500（实测 %s）" % r.status_code
    assert _err(r) == "Internal server error", "通用文案被改了：%r" % _err(r)
    body = r.get_data(as_text=True)
    assert "internal-detail-must-not-leak" not in body and "ValueError" not in body, "⛔ 泄漏了内部信息"


def test_g3_404_405_wording_unchanged(client):
    """承「好形状逐字不变」：404／405 既有文案 ⛔ 不许被新处理器改形。"""
    r = client.post("/probe/nope", data=b"{}", content_type="application/json")
    assert r.status_code == 404, r.status_code
    assert _err(r) == "Endpoint '/probe/nope' not found", _err(r)
    r2 = client.get("/probe/boom")
    assert r2.status_code == 405, r2.status_code
    assert _err(r2) == "Method GET not allowed for /probe/boom", _err(r2)


def test_g4_http_abort_status_preserved_and_located(client):
    """放行 `HTTPException` 的**回报**：其它语义码（403）原样保留，且 ⛔ 不再是 500。"""
    r = client.post("/probe/abort", data=b"{}", content_type="application/json")
    assert r.status_code == 403, "HTTPException 语义码须原样（实测 %s）" % r.status_code
    assert "probe/abort" in _err(r), "须带路由定位：%r" % _err(r)


# ==================== 门 B · routes/browser.py · v9_browser_stop ====================

def test_b1_stop_empty_payload_is_400_missing_reason(client):
    """病：`{}` ⇒ 200 ＋ `reason=\"老板手动停止\"`（**伪造一句人下的令**）⇒ 改后须 400 缺 reason。"""
    r = client.post("/v9/browser/stop", json={})
    assert r.status_code == 400, "空载荷须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert "v9/browser/stop" in e and "reason" in e, "须定位 ＋ 说缺什么：%r" % e
    assert "老板" not in r.get_data(as_text=True), "⛔ 不许再用默认值生成「像人下过令」的文案"


def test_b2_stop_non_dict_is_400(client):
    r = client.post("/v9/browser/stop", json=["x"])
    assert r.status_code == 400, "非对象须 400（实测 %s）" % r.status_code
    e = _err(r)
    assert "v9/browser/stop" in e and "需要 JSON 对象" in e and "list" in e, "须定位＋报形状：%r" % e


def test_b3_stop_bad_json_is_400(client):
    r = client.post("/v9/browser/stop", data=BAD_JSON, content_type="application/json")
    assert r.status_code == 400, "坏 JSON 须 400（实测 %s）" % r.status_code
    assert "不是合法 JSON" in _err(r), _err(r)


def test_b4_stop_reason_is_caller_supplied_never_default(client):
    """对照臂：合法载荷 ⇒ 200，且 reason **用调用方给的**（⛔ 不是默认值）。"""
    r = client.post("/v9/browser/stop", json={"reason": "probe-ok"})
    assert r.status_code == 200, "合法载荷须 200（实测 %s）：%s" % (r.status_code, r.data[:200])
    j = r.get_json() or {}
    assert j.get("reason") == "probe-ok", "reason 被替换：%r" % j
    assert "老板手动停止" not in r.get_data(as_text=True), "⛔ 默认文案泄漏"


# ==================== 门 X · core/gateway/sandbox_ops.py ====================

def test_x1_list_empty_payload_is_400(client):
    """病：`{}` ⇒ 200 ＋ `path=data/projects/default/...`（**默认路径冒充调用方意图**）。"""
    r = client.post("/v9/sandbox/list", json={})
    assert r.status_code == 400, "空载荷须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert "v9/sandbox/list" in e and "空载荷" in e, "须定位＋说明：%r" % e


def test_x2_list_non_dict_is_400(client):
    r = client.post("/v9/sandbox/list", json=["x"])
    assert r.status_code == 400, "非对象须 400（实测 %s）" % r.status_code
    e = _err(r)
    assert "v9/sandbox/list" in e and "需要 JSON 对象" in e, "须定位＋报形状：%r" % e


def test_x3_list_valid_shape_still_200(client):
    """对照臂：好形状 ⇒ 200 ＋ `success=true`（⛔ 守卫不许误伤正经调用）。"""
    r = client.post(
        "/v9/sandbox/list",
        json={"path": ".", "user_id": "u", "session_id": "s", "skip_quota": True},
    )
    assert r.status_code == 200, "好形状须 200（实测 %s）：%s" % (r.status_code, r.data[:200])
    assert (r.get_json() or {}).get("success") is True, r.data[:200]


def test_x4_wrapped_read_empty_payload_is_400(client):
    """共享装饰器 `_with_http_tool_flow` 面：`{}` ⇒ 400（一处覆盖 5 条被装饰路由）。"""
    r = client.post("/v9/sandbox/read", json={})
    assert r.status_code == 400, "空载荷须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert "v9/sandbox/read" in e and "空载荷" in e, "须定位＋说明：%r" % e


def test_x5_wrapped_exec_empty_payload_is_400(client):
    r = client.post("/v9/sandbox/exec", json={})
    assert r.status_code == 400, "空载荷须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert "v9/sandbox/exec" in e and "空载荷" in e, "须定位＋说明：%r" % e


def test_x6_wrapped_search_empty_payload_is_400(client):
    r = client.post("/v9/sandbox/search", json={})
    assert r.status_code == 400, "空载荷须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    assert "v9/sandbox/search" in _err(r), _err(r)
