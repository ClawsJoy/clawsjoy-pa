# -*- coding: utf-8 -*-
r"""PM-011 · batch2 · `core\lib\v8\routes\v8_misc.py` 原文泄漏 **6 处**（PM 2026-09-30 裁「并入 N2c」）。

PM 裁（原话要点）：
  (1) 出口面 ⛔ 不回异常原文（「真回客户端 ＋ 真原文」＝ 本类唯一真病面）；
  (2) ⭐ 承 N2b 纪律：**每处必须各有专属反例门**，⛔ 不许一处有齿、多处搭车；
  (3) 反例门判据：**响应体 ⛔ 不含任何 Python 异常类名** ∧ **反向断言**（⛔ 不含桩标记原文）。

⚠ 本件只动**出口文案 ＋ 日志**：
  ⛔ 不改 HTTP 状态（仍 500）｜⛔ 不改 `_v8_resp_err` 响应形状｜
  ⛔ 不改 `"missing id"` 等**既有域文案**
     （其 HTTP 由默认 500 显式成 400，属 batch-(a) **形状轴**，见 `tests\unit\test_pm011_v8_shape.py`）
  ｜⛔ 本件不碰 `request.json or {}` 形状轴。
"""
from __future__ import annotations

import pathlib
import re
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]

_CLS_RE = re.compile(r"\b(?:[A-Z][A-Za-z]*Error|Exception|Traceback)\b")
LITERAL_FORBIDDEN = (
    "Traceback", "has no attribute", "object has no attribute",
    "AttributeError", "TypeError", "KeyError", "ValueError", "RuntimeError",
    "Internal server error",
)

EXPECT = {
    1: "v8/notifications: 内部错误（已记日志）",
    2: "v8/notifications/list: 内部错误（已记日志）",
    3: "v8/notifications/read: 内部错误（已记日志）",
    4: "v8/notifications/read-all: 内部错误（已记日志）",
    5: "v8/notifications/unread-count: 内部错误（已记日志）",
    6: "v8/discussions/get: 内部错误（已记日志）",
}


def assert_clean(body: str, tag: str):
    for k in LITERAL_FORBIDDEN:
        assert k not in body, "%s：响应体里出现 %r ／ %s" % (tag, k, body[:200])
    m = _CLS_RE.search(body)
    assert not m, "%s：响应体里出现异常类名 %r ／ %s" % (tag, m.group(0), body[:200])


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    (tmp_path / "pa").mkdir(parents=True, exist_ok=True)
    app = Flask(__name__)
    # ⭐ 与活服务同链（`agent_gateway_enhanced.py:424` 就是这么注册的）
    from core.lib.error_handler import register_error_handlers
    register_error_handlers(app)
    from core.lib.v8.routes.v8_misc import register_misc_routes
    register_misc_routes(app)
    return app.test_client()


# ==================== :26  GET /v8/notifications ====================

def test_t1_notifications_query_error_is_sanitized(client):
    r = client.get("/v8/notifications?limit=abc")
    assert r.status_code == 500, "状态须保持 500（实测 %s）" % r.status_code
    body = r.data.decode("utf-8", "replace")
    assert "invalid literal" not in body, "T1 把 ValueError 原文回客户端了：%s" % body[:200]
    assert (r.get_json() or {}).get("error") == EXPECT[1]
    assert_clean(body, "T1")


# ==================== :37  GET /v8/notifications/list ====================

def test_t2_notifications_list_query_error_is_sanitized(client):
    r = client.get("/v8/notifications/list?limit=abc")
    assert r.status_code == 500
    body = r.data.decode("utf-8", "replace")
    assert "invalid literal" not in body, "T2 泄漏：%s" % body[:200]
    assert (r.get_json() or {}).get("error") == EXPECT[2]
    assert_clean(body, "T2")


# ==================== :50  POST /v8/notifications/read ====================

def test_t3_notifications_read_body_error_is_sanitized(client, monkeypatch):
    # ⚠ 触发方式已换（batch-(a) 形状轴的连带）：`json="x"` 那条路**已被形状守卫接管**
    #   ⇒ 走 400 `需要 JSON 对象`，⛔ 再打不到 `except Exception as e` 这一支。
    #   ⇒ 改用桩让 `mark_read` 抛（T4／T5 同法）—— ⛔ 不许门因此失去齿。
    from core.lib.v8.routes import v8_misc as M

    def boom(*a, **k):
        raise AttributeError("boom-t3-read has no attribute 'x'")

    monkeypatch.setattr(M, "mark_read", boom)
    r = client.post("/v8/notifications/read", json={"id": "n-t3"})
    assert r.status_code == 500
    body = r.data.decode("utf-8", "replace")
    assert "has no attribute" not in body, "T3 泄漏 AttributeError 原文：%s" % body[:200]
    assert "boom-t3-read" not in body, "T3 泄漏桩标记：%s" % body[:200]
    assert (r.get_json() or {}).get("error") == EXPECT[3]
    assert_clean(body, "T3")


# ==================== :59  POST /v8/notifications/read-all ====================

def test_t4_read_all_error_is_sanitized(client, monkeypatch):
    from core.lib.v8.routes import v8_misc as M

    def boom(*a, **k):
        raise RuntimeError("boom-t4-read-all")

    monkeypatch.setattr(M, "mark_all_read", boom)
    r = client.post("/v8/notifications/read-all")
    assert r.status_code == 500
    body = r.data.decode("utf-8", "replace")
    assert "boom-t4-read-all" not in body, "T4 把异常原文回客户端了：%s" % body[:200]
    assert (r.get_json() or {}).get("error") == EXPECT[4]
    assert_clean(body, "T4")


# ==================== :68  GET /v8/notifications/unread-count ====================

def test_t5_unread_count_error_is_sanitized(client, monkeypatch):
    from core.lib.v8.routes import v8_misc as M

    def boom(*a, **k):
        raise RuntimeError("boom-t5-unread-count")

    monkeypatch.setattr(M, "unread_count", boom)
    r = client.get("/v8/notifications/unread-count")
    assert r.status_code == 500
    body = r.data.decode("utf-8", "replace")
    assert "boom-t5-unread-count" not in body, "T5 把异常原文回客户端了：%s" % body[:200]
    assert (r.get_json() or {}).get("error") == EXPECT[5]
    assert_clean(body, "T5")


# ==================== :160  GET /v8/discussions/get（我的 +1） ====================

def test_t6_discussions_get_error_is_sanitized(client, monkeypatch):
    real_exists = pathlib.Path.exists
    real_read_text = pathlib.Path.read_text

    def fake_exists(self):
        if str(self).endswith("__leak__.json"):
            return True
        return real_exists(self)

    def fake_read_text(self, *a, **k):
        if str(self).endswith("__leak__.json"):
            raise RuntimeError("boom-t6-discussions-get")
        return real_read_text(self, *a, **k)

    monkeypatch.setattr(pathlib.Path, "exists", fake_exists)
    monkeypatch.setattr(pathlib.Path, "read_text", fake_read_text)
    r = client.get("/v8/discussions/get?id=__leak__")
    assert r.status_code == 500, "状态须保持 500（实测 %s）" % r.status_code
    body = r.data.decode("utf-8", "replace")
    assert "boom-t6-discussions-get" not in body, "T6 把异常原文回客户端了：%s" % body[:200]
    assert (r.get_json() or {}).get("error") == EXPECT[6]
    assert_clean(body, "T6")


# ==================== 对照（⛔ 不该被一起改坏的既有行为） ====================

def test_ctl_ok_shape_unchanged(client, monkeypatch):
    """好形状：`_v8_resp_ok` 的响应**逐字不变**。"""
    from core.lib.v8.routes import v8_misc as M
    monkeypatch.setattr(M, "unread_count", lambda: {"total": 2, "unread_count": 2})
    r = client.get("/v8/notifications/unread-count")
    assert r.status_code == 200
    assert r.get_json() == {"success": True, "data": {"total": 2, "unread_count": 2}, "message": "ok"}


# ⚠ `missing id` 一例**已移交** batch-(a) 形状轴（HTTP 由 500 ⇒ 400，字句逐字不变）：
#   见 `tests\unit\test_pm011_v8_shape.py::test_s1c_read_missing_id_is_400_wording_unchanged`
#   ⇒ 本件不再持它 —— ⛔ 免得两件盯同一处、口径打架（「一次只动一处」）。

# ==================== 日志面（PM 裁「收」：只留类名，⛔ 不留参数值） ====================
#
# 依据：PM 2026-09-30 裁（三）—— `'abc'` 是**参数值**，可能含用户数据／密钥／路径
#   ⇒ 日志面口径收紧为 **「只留类名」**；「类型化摘要」（如 `<str:3>`）列下一批候选，⛔ 本批不做。
# ⚠ 这 6 条是**日志面**的门（⛔ 与客户端面那 6 条分开）—— 承「报数前先报在哪个面上扫」。

import logging


@pytest.fixture()
def logcap():
    """把 v8_misc 的日志**直接接住**（⛔ 不依赖 propagate ／ root 配置，防假绿）。"""
    from core.lib.v8.routes import v8_misc as M

    recs = []

    class _H(logging.Handler):
        def emit(self, record):
            recs.append(record)

    h = _H(level=logging.ERROR)
    old_level = M.logger.level
    M.logger.addHandler(h)
    M.logger.setLevel(logging.ERROR)
    yield recs
    M.logger.removeHandler(h)
    M.logger.setLevel(old_level)


def _only(recs, needle):
    msgs = [r.getMessage() for r in recs if needle in r.getMessage()]
    assert len(msgs) == 1, "期望恰好 1 条 %r，实测 %d 条：%r" % (needle, len(msgs), msgs)
    return msgs[0]


def test_logface_t1_classname_only_never_param_value(client, logcap):
    client.get("/v8/notifications?limit=abc")
    m = _only(logcap, "v8/notifications 内部错误")
    assert "ValueError" in m, "类名没留：%r" % m
    assert "'abc'" not in m and "abc" not in m, "⭐ 参数值进了日志：%r" % m


def test_logface_t2_classname_only_never_param_value(client, logcap):
    client.get("/v8/notifications/list?limit=abc")
    m = _only(logcap, "v8/notifications/list 内部错误")
    assert "ValueError" in m
    assert "abc" not in m, "⭐ 参数值进了日志：%r" % m


def test_logface_t3_classname_only_never_message_body(client, logcap, monkeypatch):
    # ⚠ 同上：触发改桩（形状守卫已接管 `json="x"`，⛔ 到不了这一支）。
    from core.lib.v8.routes import v8_misc as M

    def boom(*a, **k):
        raise AttributeError("boom-t3-read has no attribute 'x'")

    monkeypatch.setattr(M, "mark_read", boom)
    client.post("/v8/notifications/read", json={"id": "n-t3"})
    m = _only(logcap, "v8/notifications/read 内部错误")
    assert "AttributeError" in m
    assert "has no attribute" not in m, "⭐ 异常消息正文进了日志：%r" % m


def test_logface_t4_classname_only_never_tag(client, logcap, monkeypatch):
    from core.lib.v8.routes import v8_misc as M

    def boom(*a, **k):
        raise RuntimeError("boom-t4-read-all")

    monkeypatch.setattr(M, "mark_all_read", boom)
    client.post("/v8/notifications/read-all")
    m = _only(logcap, "v8/notifications/read-all 内部错误")
    assert "RuntimeError" in m
    assert "boom-t4-read-all" not in m, "⭐ 桩标记进了日志：%r" % m


def test_logface_t5_classname_only_never_tag(client, logcap, monkeypatch):
    from core.lib.v8.routes import v8_misc as M

    def boom(*a, **k):
        raise RuntimeError("boom-t5-unread-count")

    monkeypatch.setattr(M, "unread_count", boom)
    client.get("/v8/notifications/unread-count")
    m = _only(logcap, "v8/notifications/unread-count 内部错误")
    assert "RuntimeError" in m
    assert "boom-t5-unread-count" not in m, "⭐ 桩标记进了日志：%r" % m


def test_logface_t6_classname_only_never_tag(client, logcap, monkeypatch):
    import pathlib

    real_exists = pathlib.Path.exists
    real_read_text = pathlib.Path.read_text

    def fake_exists(self):
        if str(self).endswith("__leak__.json"):
            return True
        return real_exists(self)

    def fake_read_text(self, *a, **k):
        if str(self).endswith("__leak__.json"):
            raise RuntimeError("boom-t6-discussions-get")
        return real_read_text(self, *a, **k)

    monkeypatch.setattr(pathlib.Path, "exists", fake_exists)
    monkeypatch.setattr(pathlib.Path, "read_text", fake_read_text)
    client.get("/v8/discussions/get?id=__leak__")
    m = _only(logcap, "v8/discussions/get 内部错误")
    assert "RuntimeError" in m
    assert "boom-t6-discussions-get" not in m, "⭐ 桩标记进了日志：%r" % m
