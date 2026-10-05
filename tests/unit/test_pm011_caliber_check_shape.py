# -*- coding: utf-8 -*-
r"""PM-011 · N2（2026-09-30 · CW b2a5182）：`POST /v9/pa/caliber/check` **输入形状校到底**。

病（PM 批）：「`caliber/check` 不校元素形状 ⇒ 500 ＋ 内部文本」。
我复跑后**收窄一处、加重一处**（原始输出见件）：
  · **收窄（两套 harness 各一手）**：改前的 500 响应体⛔ **不含** traceback ／ `AttributeError`
    ⇒ 准确说法是「500 ＋ **含糊体**」，不是「内部文本泄漏」。两读数：
      – 裸 Flask（无全局错误处理器）⇒ `text/html` · **265 B** · Werkzeug 通用页；
      – **活服务同链**（`core\lib\error_handler.py` `errorhandler(Exception)`）⇒ `application/json` · **68 B** ·
        `{"error":"Internal server error","status_code":500,"success":false}`。
    ⭐ 内部文本（traceback）**落在服务端日志**（`logs\gateway_5102_console.log`），⛔ 不回客户端。
    但它照样把「**你给错了形状**」说成「**服务器出错了**」—— 与含糊话术同族。
  · **加重**：改前还有**两处假绿**（形状坏，却回 `{"ok":true,"hit_count":0}`）：
    `body=[]`（JSON 数组 ⇒ `[] or {}` 吞成 `{}`）／ `pages` 是 falsy 非列表（`""`／`0` ⇒ `or []` 吞成 `[]`）。
    ⇒ 与 **437 假绿** ／ **`_jsonl_lines` 的 `0`** ／ **验收-B「过期 0」** 同族：**0 看起来像读数**。

判据（可机检）：
  S1  任何形状错 ⇒ `{"ok": false}` ＋ HTTP **400**（⛔ 非 500、⛔ 非假绿 200）
  S2  错误文本**含出错位置**（`body` ／ `pages[2].data` …）
  S3  响应 ⛔ 不得是 HTML、⛔ 不得含内部文本
  S4  **正形状逐字不动**（与改前同答复，返回字段集不变）
  S5  正形状**必须过**（⛔ 不许为了校形状把好输入也挡了）
  S6  边界按登记走：`pages:null` ⇒ 视作 `[]`（兼容既有，**不变**）

本件**不 mock 被审对象**：走真路由（Flask `test_client` ＋ 临时 `PA_DATA_DIR`）。
"""
from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]

BAD_SHAPES = [
    ("body 是 JSON 数组", {"payload": []}),
    ("pages 是空串", {"payload": {"pages": ""}}),
    ("pages 是 0", {"payload": {"pages": 0}}),
    ("pages 是 false", {"payload": {"pages": False}}),
    ("pages 是字典", {"payload": {"pages": {}}}),
    ("元素非对象", {"payload": {"pages": [{"data": {}}, "x"]}}),
    ("data 非对象", {"payload": {"pages": [{"data": "x"}]}}),
    ("data 是列表", {"payload": {"pages": [{"data": []}]}}),
    ("body 非法 JSON", {"raw": "{ 半截"}),
]
BAD_IDS = [n for n, _ in BAD_SHAPES]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    (tmp_path / "pa").mkdir(parents=True, exist_ok=True)
    app = Flask(__name__)
    # ⭐ 与**活服务同链**：活服务装了 `errorhandler(Exception)`（core\lib\error_handler.py）
    # ⇒ 不装的话 500 会走裸 Werkzeug 页，判据与线上不同形（尺 1：判据要打在真源上）。
    from core.lib.error_handler import register_error_handlers
    register_error_handlers(app)
    from core.pa.gateway_routes import register_pa_routes
    register_pa_routes(app)
    return app.test_client()


def _post(client, payload=None, raw=None):
    if raw is not None:
        return client.post("/v9/pa/caliber/check", data=raw, content_type="application/json")
    return client.post("/v9/pa/caliber/check", json=payload)


# ============================ S1：错形状 ⇒ 400 ok:false（⛔ 非 500／非假绿） ============================

@pytest.mark.parametrize("name,kw", BAD_SHAPES, ids=BAD_IDS)
def test_s1_bad_shape_is_400_not_500_not_fakegreen(client, name, kw):
    r = _post(client, **kw)
    assert r.status_code == 400, "%s：改前是 500 或假绿 200；现应 400（实测 %s）" % (name, r.status_code)
    d = r.get_json() or {}
    assert d.get("ok") is False, "%s：形状错竟不是 ok:false（%r）" % (name, r.data[:120])


# ============================ S2／S3：可定位 ＋ ⛔ 不泄漏内部文本 ============================

@pytest.mark.parametrize("name,kw", BAD_SHAPES, ids=BAD_IDS)
def test_s2_s3_locates_and_never_returns_html_or_internals(client, name, kw):
    r = _post(client, **kw)
    assert r.headers.get("Content-Type", "").startswith("application/json"), \
        "%s：仍然回 HTML（%s）—— 那就还是「含糊页」" % (name, r.headers.get("Content-Type"))
    raw = r.data.decode("utf-8", "replace")
    assert "Internal server error" not in raw, \
        "%s：掉进全局 500 兜底了（%r）—— 那就还是「含糊体」" % (name, raw[:120])
    for k in ("AttributeError", "Traceback", "has no attribute", "<html", "<!doctype"):
        assert k not in raw, "%s：响应里出现 %r" % (name, k)
    e = str((r.get_json() or {}).get("error") or "")
    assert any(t in e for t in ("body", "pages[")) or e.startswith("caliber/check: pages "), \
        "%s：错误文本没定位到出错位置：%r" % (name, e)


def test_s2b_index_is_the_real_one(client):
    """位置必须**指向真出错的那一格**（⛔ 不许一律报 pages[0]）。"""
    r = _post(client, payload={"pages": [{"data": {}}, {"data": {}}, {"data": 5}]})
    assert r.status_code == 400
    e = (r.get_json() or {}).get("error", "")
    assert "pages[2].data" in e, "位置报错了（应为 pages[2].data）：%r" % e


# ============================ S5／S6：好形状必须过 ============================

@pytest.mark.parametrize("name,payload", [
    ("empty", {"pages": []}),
    ("no-data", {"pages": [{}]}),
    ("empty-data", {"pages": [{"data": {}}]}),
    ("extra", {"pages": [{"data": {"body": "x"}, "extra": 1}]}),
    ("no-pages-key", {}),
    ("null", {"pages": None}),
], ids=["empty", "no-data", "empty-data", "extra", "no-pages-key", "null"])
def test_s5_good_shapes_still_pass(client, name, payload):
    r = _post(client, payload=payload)
    assert r.status_code == 200, "%s：好形状被挡住了（HTTP %s）" % (name, r.status_code)
    d = r.get_json() or {}
    assert d.get("ok") is True and d.get("hit_count") == 0


# ============================ S4：正形状逐字不动 ============================

def test_s4_valid_shape_answer_is_unchanged(client):
    d = _post(client, payload={"pages": [{"data": {"body": "建行 OPC 专属贷 最高 300 万"}}]}).get_json()
    assert d["ok"] is True and d["hit_count"] == 1
    assert d["hits"][0][1] == "#4" and d["hits"][0][3] == "unverified"
    assert set(d.keys()) == {"ok", "hits", "hit_count"}, "返回字段集被顺手改了：%r" % sorted(d.keys())