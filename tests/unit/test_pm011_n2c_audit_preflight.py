# -*- coding: utf-8 -*-
r"""PM-011 · N2c（2026-09-30 · CW b2a5182）：`POST /v9/pa/audit/preflight` **输入形状校到底**。

PM 裁（原话要点）：N2c **排在 N2b 之后**（按**严重度**排，⛔ 不按发现顺序 —— change 线是原文泄漏，更重）；
判据要**三态齐**：
  C1 坏形状 ⇒ **400 ＋ 定位**
  C2 好形状 ⇒ **逐字不变**
  C3 ⛔ **无假绿**（用门钉住：坏形状⛔ 不许回 200 ／ ⛔ 不许 ok:true）

改前一手读数（我 §五 报过）：坏形状有 **5 种 ⇒ 500**（`body='x'` ／ `pages=[1]` ／ `pages=['x']` ／
`pages=[{data:'x'}]` ／ 非法 JSON），但**没有假绿**（falsy 那几种被 `or []` ＋ `not pages` 拦下 ⇒ 400）。
⚠ 本件只动**输入边界**：⛔ 不碰 `A.preflight()` 语义、⛔ 不改返回字段、⛔ 不改既有成功文案。
"""
from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]

BAD_SHAPES = [
    ("body 是 str", {"payload": "x"}, "body 需要 JSON 对象（拿到 str）"),
    ("body 是 int", {"payload": 1}, "body 需要 JSON 对象（拿到 int）"),
    ("body 是 bool", {"payload": True}, "body 需要 JSON 对象（拿到 bool）"),
    ("body 是 list", {"payload": []}, "body 需要 JSON 对象（拿到 list）"),
    ("pages 是 str", {"payload": {"pages": ""}}, "pages 需要列表（拿到 str）"),
    ("pages 是 0", {"payload": {"pages": 0}}, "pages 需要列表（拿到 int）"),
    ("pages 是 dict", {"payload": {"pages": {}}}, "pages 需要列表（拿到 dict）"),
    ("元素非对象", {"payload": {"pages": [1]}}, "pages[0] 不是对象（拿到 int）"),
    ("元素非对象(2)", {"payload": {"pages": ["x"]}}, "pages[0] 不是对象（拿到 str）"),
    ("data 非对象", {"payload": {"pages": [{"data": "x"}]}}, "pages[0].data 不是对象（拿到 str）"),
    ("data 是 list", {"payload": {"pages": [{"data": []}]}}, "pages[0].data 不是对象（拿到 list）"),
    ("body 非法 JSON", {"raw": "{ 半截"}, "body 不是合法 JSON"),
]
# ★ id 用 ASCII：否则 pytest 短摘要里会把中文 id 转成 \uXXXX，
#   而本件的“专属反例门”要靠 id 做**机检**匹配。
BAD_IDS = ["body-str", "body-int", "body-bool", "body-list",
           "pages-str", "pages-int", "pages-dict",
           "elem-int", "elem-str", "data-str", "data-list", "json-bad"]

# ⭐ C2：好形状**逐字**（改前／改后必须一字不差；采集自改后实跑，见件 §三）
# ⭐ 逐字基准串（原样：Flask jsonify 默认 ensure_ascii ⇒ 中文转 \uXXXX；且**带尾换行**）
_GOOD_BODY = (
    r"""{"fail_count":1,"issues":[["P01","fail","layout 'None' \u4e0d\u5728\u767d\u540d\u5355"]],"ok":true,"pages":1,"pass":false,"warn_count":0}"""
    + "\n"
)

GOOD_EXACT = {
    "pages=[{}]": ({"pages": [{}]}, _GOOD_BODY),
    "pages=[{data:{}}]": ({"pages": [{"data": {}}]}, _GOOD_BODY),
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    (tmp_path / "pa").mkdir(parents=True, exist_ok=True)
    app = Flask(__name__)
    # ⭐ 与活服务同链（否则 500 走裸 Werkzeug 页 ⇒ 判据与线上不同形）
    from core.lib.error_handler import register_error_handlers
    register_error_handlers(app)
    from core.pa.gateway_routes import register_pa_routes
    register_pa_routes(app)
    return app.test_client()


def _post(client, payload=None, raw=None):
    if raw is not None:
        return client.post("/v9/pa/audit/preflight", data=raw, content_type="application/json")
    return client.post("/v9/pa/audit/preflight", json=payload)


# ==================== C1 ＋ C3：坏形状 ⇒ 400 ＋ 定位，且⛔ 无假绿 ====================

@pytest.mark.parametrize("name,kw,needle", BAD_SHAPES, ids=BAD_IDS)
def test_c1_c3_bad_shape_400_with_location_never_fakegreen(client, name, kw, needle):
    r = _post(client, **kw)
    assert r.status_code == 400, "%s：改前是 500；现应 400（实测 %s）" % (name, r.status_code)
    d = r.get_json() or {}
    assert d.get("ok") is not True, "%s：⭐ 假绿（形状坏却 ok:true）：%r" % (name, r.data[:120])
    e = str(d.get("error") or "")
    assert needle in e, "%s：错误文本没定位到：want %r got %r" % (name, needle, e)
    raw = r.data.decode("utf-8", "replace")
    for k in ("AttributeError", "Traceback", "has no attribute", "<html", "<!doctype", "Internal server error"):
        assert k not in raw, "%s：响应里出现 %r" % (name, k)


def test_c1_index_is_the_real_one(client):
    """位置必须指向**真出错那一格**（⛔ 不许一律 pages[0]）。"""
    r = _post(client, payload={"pages": [{"data": {}}, {"data": {}}, {"data": 5}]})
    assert r.status_code == 400
    e = (r.get_json() or {}).get("error", "")
    assert "pages[2].data" in e, "位置报错了（应为 pages[2].data）：%r" % e


def test_c0_empty_pages_keeps_existing_message(client):
    """既有文案**不变**：`pages` 空 ⇒ 仍是 400「audit/preflight 需要 pages 列表」。"""
    r = _post(client, payload={"pages": []})
    assert r.status_code == 400
    assert (r.get_json() or {}).get("error") == "audit/preflight 需要 pages 列表"


# ============================ C2：好形状逐字不变 ============================

@pytest.mark.parametrize("name", sorted(GOOD_EXACT), ids=sorted(GOOD_EXACT))
def test_c2_good_shape_byte_identical(client, name):
    payload, want = GOOD_EXACT[name]
    r = _post(client, payload=payload)
    assert r.status_code == 200, "%s：好形状被挡住了（HTTP %s）" % (name, r.status_code)
    got = r.data.decode("utf-8")
    assert got == want, "%s：好形状答复**不再逐字**：\n  want=%s\n  got =%s" % (name, want, got)