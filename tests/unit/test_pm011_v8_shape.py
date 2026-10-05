# -*- coding: utf-8 -*-
r"""PM-011 · batch2-(a) **形状轴** · `core\lib\v8\routes\v8_misc.py`。

PM 2026-09-30 裁（v13 §一(a) ＋ v14 §一「并下一批」）：
  **坏形状 ⇒ 400 ＋ 定位，⛔ 不是 500（含糊体）／200（假装成功）。**
  ⭐ 承 N2b／N2c 纪律：**每处必须各有专属反例门**，⛔ 不许一处有齿、多处搭车
     （机检版：实际红集 ≡ 期望红集，见 `run_redgreen_batch2.py` 的 `exclusive`）。
  ⭐ `"missing id"` 是**既有域文案** ⇒ **字句逐字不变**，只把 HTTP 由默认 500 显式成 400。

本件只动**形状判定 ＋ 状态码**（5 处）：
  S1 `v8_notifications_read`   JSON 解析 ＋ 顶层类型守卫
  S2 `v8_notifications_read`   `missing id`（字句不变，500 ⇒ 400）
  S3 `v8_discussions_save`     JSON 解析 ＋ 顶层类型守卫
  S4 `v8_discord_notify`       JSON 解析 ＋ 顶层类型守卫
  S5 `v8_discord_notify`       缺必填 ⇒ 400（旧行为：**HTTP 200** ＋ `{"success": false}`）

⛔ 本件不碰：
  · (b) 静默吞 —— `v8_discord_notify` 末尾 `except Exception: return jsonify({"success": False})`
    （PM v13 §一(b) 裁：**只登记**；修它要先决定「吞了之后该说什么」＝ 产品语义）；
  · `v8_discussions_save` 用 `datetime.now()` 而本模块未 import `datetime` 的**死路**
    （PM v13 §二 裁：标「在场≠生效」入册，**本批不修**）—— 故其对照门**只钉「⛔ 不是 400」**。
"""
from __future__ import annotations

import pathlib
import re

import pytest
from flask import Flask

LOCATORS = {
    "read": "v8/notifications/read",
    "save": "v8/discussions/save",
    "notify": "v8/discord/notify",
}
BAD_JSON = b"{not json"


def _err(r):
    j = r.get_json() or {}
    return j.get("error") or ""


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    (tmp_path / "pa").mkdir(parents=True, exist_ok=True)
    app = Flask(__name__)
    from core.lib.error_handler import register_error_handlers
    register_error_handlers(app)
    from core.lib.v8.routes.v8_misc import register_misc_routes
    register_misc_routes(app)
    return app.test_client()


@pytest.fixture()
def dpath(tmp_path, monkeypatch):
    """`discussions/save` 会落盘 ⇒ 把 `data/v8/discussions` 改指 tmp，⛔ 不写生产数据面。"""
    from core.lib.v8.routes import v8_misc as M
    real = pathlib.Path
    target = tmp_path / "discussions"
    target.mkdir(parents=True, exist_ok=True)

    def _mk(p, *a, **k):
        if str(p).replace("\\", "/") == "data/v8/discussions":
            return target
        return real(p, *a, **k)

    monkeypatch.setattr(M, "Path", _mk)
    return target


# ==================== S1 · /v8/notifications/read · 形状 ====================

def test_s1a_read_body_not_json_is_400(client):
    r = client.post("/v8/notifications/read", data=BAD_JSON, content_type="application/json")
    assert r.status_code == 400, "坏 JSON 须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert LOCATORS["read"] in e and "不是合法 JSON" in e, "缺定位：%r" % e
    # ⚠ 「⛔ 不许含内部异常类名」由 KP1 统一管（PM 2026-09-30 写死的口径）——⛔ 一处一主，不双管。


def test_s1b_read_body_non_dict_is_400(client):
    r = client.post("/v8/notifications/read", json=["x"])
    assert r.status_code == 400, "非对象须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert LOCATORS["read"] in e and "需要 JSON 对象" in e, "缺定位：%r" % e
    assert "list" in e, "须报拿到什么类型：%r" % e


# ==================== S2 · /v8/notifications/read · missing id ====================

def test_s1c_read_missing_id_is_400_wording_unchanged(client):
    for body in ({}, {"id": ""}):
        r = client.post("/v8/notifications/read", json=body)
        assert r.status_code == 400, "缺 id 须 400（%r 实测 %s）" % (body, r.status_code)
        assert _err(r) == "missing id", "域文案被改了：%r" % _err(r)


# ==================== S3 · /v8/discussions/save · 形状 ====================

def test_s3a_save_body_not_json_is_400(client, dpath):
    r = client.post("/v8/discussions/save", data=BAD_JSON, content_type="application/json")
    assert r.status_code == 400, "坏 JSON 须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert LOCATORS["save"] in e and "不是合法 JSON" in e, "缺定位：%r" % e


def test_s3b_save_body_non_dict_is_400(client, dpath):
    r = client.post("/v8/discussions/save", json=["x"])
    assert r.status_code == 400, "非对象须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert LOCATORS["save"] in e and "需要 JSON 对象" in e, "缺定位：%r" % e


# ==================== S4/S5 · /v8/discord/notify · 形状 ＋ 缺必填 ====================

def test_s4a_notify_body_not_json_is_400(client):
    r = client.post("/v8/discord/notify", data=BAD_JSON, content_type="application/json")
    assert r.status_code == 400, "坏 JSON 须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert LOCATORS["notify"] in e and "不是合法 JSON" in e, "缺定位：%r" % e


def test_s4b_notify_body_non_dict_is_400(client):
    r = client.post("/v8/discord/notify", json=["x"])
    assert r.status_code == 400, "非对象须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert LOCATORS["notify"] in e and "需要 JSON 对象" in e, "缺定位：%r" % e


def test_s4c_notify_missing_fields_is_400_never_200(client):
    """⭐ 旧行为 = **HTTP 200 ＋ `{"success": false}`** ⇒ 与假绿同族（200 会被读成「发成功」）。"""
    r = client.post("/v8/discord/notify", json={})
    assert r.status_code == 400, "缺必填须 400，⛔ 不许 200 假成功（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert LOCATORS["notify"] in e and "channel_id" in e, "缺定位／缺字段名：%r" % e


# ==================== 对照（⛔ 不该被形状守卫误伤） ====================

def test_ctl_s1_good_id_ok(client, monkeypatch):
    from core.lib.v8.routes import v8_misc as M
    monkeypatch.setattr(M, "mark_read", lambda nid: {"id": nid, "read": True})
    r = client.post("/v8/notifications/read", json={"id": "n-1"})
    assert r.status_code == 200, "好形状被误拒：%s" % r.data[:200]
    assert r.get_json()["success"] is True


def test_ctl_s3_shape_guard_does_not_falsely_reject(client, dpath):
    """对照：好形状 ⛔ 不许被形状守卫拒成 400。

    ⚠ 照实：本模块 `datetime` 未 import ⇒ 好形状仍走不到 200（PM 裁：在场≠生效，入册、本批不修）
      ⇒ 本门**只钉「⛔ 不是 400」**，⛔ 不替那条死路背书、也不把它当本批成果。
    """
    r = client.post("/v8/discussions/save", json={"topic": "t"})
    assert r.status_code != 400, "形状守卫误伤好形状：%s" % r.data[:200]
    assert r.status_code in (200, 500), "意外状态：%s" % r.status_code
    assert len(list(dpath.glob("*.json"))) <= 1, "落盘面越界"


def test_ctl_s4_good_payload_ok(client, monkeypatch):
    """对照：良构载荷 ⇒ 200 且真的去发（⛔ 但用桩，⛔ 不碰真 webhook）。"""
    import requests as R
    seen = {}

    class _Resp:
        status_code = 204

    def fake_post(url, **kw):
        seen["url"] = url
        seen["json"] = kw.get("json")
        return _Resp()

    monkeypatch.setattr(R, "post", fake_post)
    r = client.post("/v8/discord/notify", json={"channel_id": "c-1", "message": "m-1"})
    assert r.status_code == 200, "好形状被误拒：%s" % r.data[:200]
    assert r.get_json() == {"success": True}
    assert seen["json"] == {"content": "m-1"}, "载荷形状变了：%r" % seen.get("json")
    assert "discord.com/api/webhooks" in seen["url"], "没走原路由：%r" % seen.get("url")


# ==================== 面归属（⭐ 承「报数前先报在哪个面上扫」） ====================

def test_face_live_module_is_this_file():
    import core.lib.v8.routes.v8_misc as M
    assert pathlib.Path(M.__file__).resolve() == (
        pathlib.Path(__file__).resolve().parents[2] / "core" / "lib" / "v8" / "routes" / "v8_misc.py"
    ).resolve(), "被测模块不是本仓那件：%s" % M.__file__


# ==================== 口径门（PM 2026-09-30 写死 · ⛔ 以后不再问） ====================
#
# 「错误文案**只许含调用方可见面的信息**（出错位置 ＋ 收到的**形状类型**），
#   ⛔ 不许含我方实现对内面的信息（**异常类名** ／ 栈 ／ 路径 ／ 参数值）。」
#
# ⭐ 这条把「载荷类型词留、内部类名不留」从"我报备的一处"升成**全族可机检的口径**：
#   ① 形状类型词（`拿到 list` ／ `拿到 str` ／ `拿到 dict`）＝ 调用方自己发来的东西 ⇒ **留**；
#   ② 异常类名（`BadRequest` ／ `AttributeError` ／ `ValueError` …）／栈／盘上路径／参数值 ⇒ **⛔ 不留**。
    # ⚠ 前导 \b 已撤：Flask `ensure_ascii=True` 会把中文写成 `\uff08` 这类转义，
    #   紧挨类名的那个字符是 `8`（word char）⇒ \bBadRequest 永远匹配不到（血案：S6 齿 rc=0 静默）。
CLIENT_FORBIDDEN = re.compile(
    r"(?:[A-Za-z_]*Error|Exception|Traceback|BadRequest|UnsupportedMediaType)\b"
    r"|[A-Za-z]:\\"
    r"|[\w\-]*\.py\b"
)
KJ_CASES = [
    ("read 坏JSON", "/v8/notifications/read", BAD_JSON),
    ("read 非对象", "/v8/notifications/read", u'["x"]'),
    ("read 缺id", "/v8/notifications/read", u"{}"),
    ("save 坏JSON", "/v8/discussions/save", BAD_JSON),
    ("save 非对象", "/v8/discussions/save", u'["x"]'),
    ("notify 坏JSON", "/v8/discord/notify", BAD_JSON),
    ("notify 非对象", "/v8/discord/notify", u'["x"]'),
    ("notify 缺必填", "/v8/discord/notify", u"{}"),
]


def test_kp1_client_text_carries_no_internal_face(client, dpath):
    """KP1：坏形状／缺必填的**客户端面文案** ⛔ 不得含我方实现对内面的信息。"""
    for tag, path, raw in KJ_CASES:
        payload = raw if isinstance(raw, bytes) else raw.encode("utf-8")
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        r = client.post(path, data=payload, content_type="application/json")
        body = r.data.decode("utf-8", "replace")
        # ⚠ **状态码不在此管**（由 S1a/S1b/S1c/S3a/S3b/S4a/S4b/S4c 各持）：
        #   若在此也断言 400，则每一处的形状齿都会连带把本门判红 ⇒ 「搭车」⇒ ⛔ 一处一主。
        m = CLIENT_FORBIDDEN.search(body)
        assert not m, "%s：客户端面出现对内面信息 %r ／ %s" % (tag, m.group(0), body[:200])
        # ② 参数值 ⛔ 不回显：我们发的原始字节 ⛔ 不许出现在响应里
        if text not in (u"{}",):
            assert text not in body, "%s：回显了调用方发送的参数值 ／ %s" % (tag, body[:200])


# ⚠ **KP2（形状类型词必须留）已撤** —— 它与 s1b 的 `"list" in e` ／ s4c 的 `"channel_id" in e`
#   **重复**，且被 S1／S5 齿**连带判红**（＝搭车）⇒ 承「一处一主」，交那两个形状门持。
