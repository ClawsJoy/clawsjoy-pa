# -*- coding: utf-8 -*-
r"""PM-011v19 · `routes/browser.py` 三处并批的专属门（CW b2a5182 · 2026-09-30）。

PM 11:2x 裁（v19 §一）：
  · 3 处同族**并批**（同文件 / 同族 / 同判据）；⚠ 条件＝**本批之后 `browser.py` 同族必须归零**（AST＝0）；
  · 优先级：`grant` 最高 —— `note` 默认**逐字「老板授权」** ＝ **伪造「授权本身」**
    （比 v17 判过的「老板手动停止」更重：那伪造的是一次动作，这伪造的是**授权本身**）。
    ⭐ 依据：lib 侧签名 `grant_browser_session(..., note: str = "")` 的中性是**空串** ⇒ ⛔ 伪造发生在**路由层**；
  · `resume` / `revoke` —— `user_id=""` ⇒ **空载荷照做**（对「谁」被默认成空串）。

⭐ 一处判据一个源：本文件 4 条 POST 全走 `_post_body()` ＋ `_require_text()`，400 出口只有 `_shape_400` 一个。
⭐ 每组**各配专属齿**（`run_redgreen_v19.py`）⇒ ⛔ 不搭车：每齿只红自己那一组。
⚠ 本件**不碰** GET 面（`request.args or {}`）：不同族 —— `request.args` 恒为 `MultiDict`，⛔ 非「空载荷退默认值」。
⚠ 本件全部读写在 test_client 内 ⇒ ⛔ 不写生产取证面（`events.jsonl` 等）。
"""
from __future__ import annotations

import ast
import io
import json
import os

import pytest
from flask import Flask

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BR = os.path.join(ROOT, "routes", "browser.py")
BAD_JSON = b"{not json"
BANNED = "老板授权"


def _err(r):
    return (r.get_json() or {}).get("error") or ""


def _text(r):
    r"""回执文本（**先解码 JSON**）。

    ⚠ `jsonify` 默认 `ensure_ascii=True` ⇒ 中文在原始 body 里是 `\uXXXX`
    ⇒ 直接拿 raw body 断言中文字面串**恒真 = 没牙**（本门首版就这么骗过一次）。
    """
    return json.dumps(r.get_json() or {}, ensure_ascii=False, sort_keys=True)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # ⭐ 换 cwd 即隔离（沙箱根为相对路径）⇒ ⛔ 不写生产数据面。
    monkeypatch.chdir(tmp_path)
    app = Flask(__name__)
    app.config["PROPAGATE_EXCEPTIONS"] = False
    from core.lib.error_handler import register_error_handlers

    register_error_handlers(app)

    from routes.browser import bp as _bp

    app.register_blueprint(_bp)

    import core.lib.v8.browser_local as _bl

    monkeypatch.setattr(
        _bl,
        "grant_browser_session",
        lambda uid, hosts=None, actions=None, ttl_s=1800, note="": {
            "success": True, "granted": True, "user_id": uid, "note": note},
    )
    monkeypatch.setattr(
        _bl,
        "resume_browser_session",
        lambda uid: {"success": True, "resumed": True, "user_id": uid},
    )
    monkeypatch.setattr(
        _bl,
        "revoke_browser_session",
        lambda uid: {"success": True, "revoked": True, "user_id": uid},
    )
    monkeypatch.setattr(
        _bl,
        "stop_browser_session",
        lambda uid, reason: {"success": True, "stopped": True, "reason": reason, "user_id": uid},
    )
    return app.test_client()


# ==================== 门 A · 「同族归零」（PM §一 的条件） ====================

def test_a0_ast_family_is_zero_in_browser_py():
    """⭐ PM 条件：`request.json or {}` 同族在 `browser.py` **归零**。

    ⚠ 判据用 **AST**，⛔ 不用文本 count —— 文本 count 会被注释 / docstring 骗
    （PM v19 §三.2 已收为尺：AST＝0 / 文本＝1 不矛盾）。
    """
    src = io.open(BR, encoding="utf-8", newline="").read()
    sites = []
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.BoolOp) and isinstance(n.op, ast.Or) and len(n.values) == 2:
            left, right = n.values
            if (isinstance(left, ast.Attribute) and left.attr == "json"
                    and isinstance(left.value, ast.Name) and left.value.id == "request"
                    and isinstance(right, ast.Dict) and not right.keys):
                sites.append(n.lineno)
    assert sites == [], "同族未归零（AST 命中行）＝%s" % sites


# ==================== 门 G · `/v9/browser/grant`（最高优先级） ====================

def test_g1_grant_empty_payload_is_400_missing_user_id(client):
    """病：`{}` ⇒ `d.get("user_id","")` ＋ `note` 默认「老板授权」⇒ 200 ＋ **伪造授权**。"""
    r = client.post("/v9/browser/grant", json={})
    assert r.status_code == 400, "空载荷须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert "v9/browser/grant" in e and "user_id" in e, "须带路由定位 ＋ 说缺什么：%r" % e


def test_g2_grant_missing_note_is_400(client):
    """⭐ 本批核心：`note` **必填** —— 默认「老板授权」＝ 伪造「授权本身」。"""
    r = client.post("/v9/browser/grant", json={"user_id": "u1"})
    assert r.status_code == 400, "缺 note 须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert "缺 note" in e, "须说缺 note：%r" % e
    assert BANNED not in _text(r), "⛔ 不许落默认「老板授权」"


def test_g3_grant_missing_user_id_is_400(client):
    r = client.post("/v9/browser/grant", json={"note": "n1"})
    assert r.status_code == 400, "缺 user_id 须 400（实测 %s）" % r.status_code
    assert "缺 user_id" in _err(r), _err(r)


def test_g4_grant_bad_json_is_400(client):
    r = client.post("/v9/browser/grant", data=BAD_JSON, content_type="application/json")
    assert r.status_code == 400, "坏 JSON 须 400（实测 %s）" % r.status_code
    assert "不是合法 JSON" in _err(r), _err(r)


def test_g5_grant_non_dict_is_400(client):
    r = client.post("/v9/browser/grant", json=["x"])
    assert r.status_code == 400, "非对象须 400（实测 %s）" % r.status_code
    e = _err(r)
    assert "需要 JSON 对象" in e and "list" in e, "须报收到的形状：%r" % e


def test_g6_grant_valid_shape_is_200_note_caller_supplied(client):
    """对照臂：好形状 ⇒ 200，且 `note` **用调用方给的**（⛔ 不是默认值）。"""
    r = client.post("/v9/browser/grant", json={"user_id": "u1", "note": "probe-ok"})
    assert r.status_code == 200, "好形状须 200（实测 %s）：%s" % (r.status_code, r.data[:200])
    j = r.get_json() or {}
    assert j.get("note") == "probe-ok", "note 被替换：%r" % j
    assert j.get("user_id") == "u1", j


def test_g7_grant_response_never_says_boss_authorization(client):
    """⭐ 反例门（本批核心）：**任何臂**的回执都 ⛔ 不得出现「老板授权」—— 空载荷臂 ＋ 好形状臂。

    ⚠ 两臂合判：只验好形状臂 ＝ 只证明「照抄调用方」；必须同时验**空载荷臂**，
      否则「空载荷会不会被填成『老板授权』」这条**没被证明**。
    """
    for body in ({}, {"user_id": "u1", "note": "probe-ok"}):
        t = _text(client.post("/v9/browser/grant", json=body))
        assert BANNED not in t, "载荷 %r ⇒ 回执出现伪造文案：%s" % (body, t[:200])


# ==================== 门 R · `/v9/browser/resume` ====================

def test_r1_resume_empty_payload_is_400_missing_user_id(client):
    """病：`{}` ⇒ `d.get("user_id","")` ⇒ **空载荷照做**（对「谁」被默认成空串）。"""
    r = client.post("/v9/browser/resume", json={})
    assert r.status_code == 400, "空载荷须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert "v9/browser/resume" in e and "user_id" in e, "须定位 ＋ 说缺什么：%r" % e


def test_r2_resume_missing_user_id_is_400(client):
    r = client.post("/v9/browser/resume", json={"hosts": []})
    assert r.status_code == 400, "缺 user_id 须 400（实测 %s）" % r.status_code
    assert "缺 user_id" in _err(r), _err(r)


def test_r3_resume_bad_json_is_400(client):
    r = client.post("/v9/browser/resume", data=BAD_JSON, content_type="application/json")
    assert r.status_code == 400, r.status_code
    assert "不是合法 JSON" in _err(r), _err(r)


def test_r4_resume_non_dict_is_400(client):
    r = client.post("/v9/browser/resume", json=["x"])
    assert r.status_code == 400, r.status_code
    assert "需要 JSON 对象" in _err(r), _err(r)


def test_r5_resume_valid_shape_is_200_user_id_passed_through(client):
    """对照臂：好形状 ⇒ 200，且 `user_id` 传到了 lib。"""
    r = client.post("/v9/browser/resume", json={"user_id": "u2"})
    assert r.status_code == 200, "好形状须 200（实测 %s）：%s" % (r.status_code, r.data[:200])
    assert (r.get_json() or {}).get("user_id") == "u2", r.data[:200]


# ==================== 门 V · `/v9/browser/revoke` ====================

def test_v1_revoke_empty_payload_is_400_missing_user_id(client):
    r = client.post("/v9/browser/revoke", json={})
    assert r.status_code == 400, "空载荷须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert "v9/browser/revoke" in e and "user_id" in e, "须定位 ＋ 说缺什么：%r" % e


def test_v2_revoke_missing_user_id_is_400(client):
    r = client.post("/v9/browser/revoke", json={"reason": "r"})
    assert r.status_code == 400, "缺 user_id 须 400（实测 %s）" % r.status_code
    assert "缺 user_id" in _err(r), _err(r)


def test_v3_revoke_bad_json_is_400(client):
    r = client.post("/v9/browser/revoke", data=BAD_JSON, content_type="application/json")
    assert r.status_code == 400, r.status_code
    assert "不是合法 JSON" in _err(r), _err(r)


def test_v4_revoke_non_dict_is_400(client):
    r = client.post("/v9/browser/revoke", json=["x"])
    assert r.status_code == 400, r.status_code
    assert "需要 JSON 对象" in _err(r), _err(r)


def test_v5_revoke_valid_shape_is_200_user_id_passed_through(client):
    r = client.post("/v9/browser/revoke", json={"user_id": "u3"})
    assert r.status_code == 200, "好形状须 200（实测 %s）：%s" % (r.status_code, r.data[:200])
    assert (r.get_json() or {}).get("user_id") == "u3", r.data[:200]


# ============ 门 S · `/v9/browser/stop`（本批**结构统一**，⛔ 非行为修复） ============
# ⚠ 本批把 stop 的内联形状块换成共享入口：**行为 ⛔ 无变更**（文案逐字不变）。
#   ⇒ 本门是**无变更的自证**：把 stop 摘回旧内联块 ⇒ ⛔ 不变红（`run_redgreen_v19.py` 的 NOCHANGE 臂）。

def test_s1_stop_empty_payload_is_400_missing_reason(client):
    r = client.post("/v9/browser/stop", json={})
    assert r.status_code == 400, r.status_code
    e = _err(r)
    assert "v9/browser/stop" in e and "reason" in e, e


def test_s2_stop_non_dict_and_bad_json_wording(client):
    r = client.post("/v9/browser/stop", json=["x"])
    assert r.status_code == 400 and "需要 JSON 对象" in _err(r), _err(r)
    r2 = client.post("/v9/browser/stop", data=BAD_JSON, content_type="application/json")
    assert r2.status_code == 400 and "不是合法 JSON" in _err(r2), _err(r2)


def test_s3_stop_valid_shape_is_200_reason_caller_supplied(client):
    r = client.post("/v9/browser/stop", json={"reason": "probe-ok"})
    assert r.status_code == 200, r.status_code
    assert (r.get_json() or {}).get("reason") == "probe-ok", r.data[:200]
    assert "老板手动停止" not in _text(r)