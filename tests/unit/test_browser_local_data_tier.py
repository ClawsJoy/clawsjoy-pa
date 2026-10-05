# -*- coding: utf-8 -*-
"""块2(分级接外发)专测 + 验收（2026-09-11）

验收：
  组1 L1 自动 / 组2 L2 自动 / 组3 L3 授权(按任务一次) / 组4 L4 禁止(个人信息不漏)
  组5 L4 拒后给方案 / 组6 L3 授权任务结束失效(回归)
"""
import json
import sys

sys.path.insert(0, ".")

import pytest

from core.lib.v8 import browser_local as bl
from core.lib.v8.browser_local import _classify_outbound, _data_grant_allows, grant_data_session, revoke_data_session

EXT = {"url": "https://chat.deepseek.com"}


# ---- 组1/2/3/4：分级器接线(纯函数) ----
def test_classify_l1_auto():
    lvl, _ = _classify_outbound("fill", {"text": "这是一份产品培训讲义", **EXT})
    assert lvl == "L1"


def test_classify_l2_auto():
    lvl, _ = _classify_outbound("fill", {"text": "已脱敏的方案，联系方式已打码", **EXT})
    assert lvl == "L2"


def test_classify_l3_raw():
    lvl, reason = _classify_outbound("fill", {"text": "项目成本 120 万，报价如下", **EXT})
    assert lvl == "L3"
    assert ("成本" in reason) or ("报价" in reason)


def test_classify_l4_phone():
    lvl, reason = _classify_outbound("fill", {"text": "请拨打 13800138000 联系", **EXT})
    assert lvl == "L4" and "手机号" in reason


def test_classify_l4_publish():
    lvl, _ = _classify_outbound("publish", {"title": "公告", "content": "身份证 11010519491231002X", **EXT})
    assert lvl == "L4"


def test_classify_local_not_tiered():
    """本机(localhost)不出机器, 不分级。"""
    lvl, _ = _classify_outbound("fill", {"text": "请打 13800138000", "url": "http://127.0.0.1/x"})
    assert lvl is None


def test_classify_non_content_action_none():
    assert _classify_outbound("click", {"selector": "button", **EXT})[0] is None
    assert _classify_outbound("navigate", {"url": "https://chat.deepseek.com"})[0] is None


# ---- 组4/5：execute L4 硬拒 + 给方案 ----
def _conn(u):
    class FakeConn:
        def __init__(self):
            self.sent = []

        def send(self, d):
            self.sent.append(json.loads(d))

    c = FakeConn()
    bl.register_ws_connection(u, c)
    return c


def test_execute_l4_blocked_with_suggestion():
    bl.unregister_ws_connection("u_l4")
    _conn("u_l4")
    try:
        r = bl.execute("u_l4", "fill", {"text": "身份证 11010519491231002X", **EXT}, timeout=2, session_id="s1")
        assert r.get("blocked") is True and r.get("level") == "L4"
        assert "脱敏" in r.get("suggestion", ""), "L4 拒后必须给脱敏方案"
        assert r.get("success") is False
    finally:
        bl.unregister_ws_connection("u_l4")


# ---- 组3/6：L3 授权(按任务一次) + 任务结束失效回归 ----
def test_execute_l3_pending_with_data_marker():
    bl.unregister_ws_connection("u_l3")
    _conn("u_l3")
    try:
        r = bl.execute("u_l3", "fill", {"text": "项目成本 120 万", **EXT}, timeout=2, session_id="sA")
        assert r.get("pending") is True
        assert "原始数据" in r.get("reason", "")
        op = bl.pending_browser_op("u_l3")
        assert op and op.get("data_l3") is True
        assert op.get("data_session_id") == "sA"
    finally:
        bl.unregister_ws_connection("u_l3")


def test_data_grant_task_scoped_expiry():
    bl.unregister_ws_connection("u_dg")
    _conn("u_dg")
    try:
        grant_data_session("u_dg", "sessionA")
        assert _data_grant_allows("u_dg", "sessionA") is True, "本任务内应授权生效"
        assert _data_grant_allows("u_dg", "sessionB") is False, "换任务(session)应失效, 需重新授权"
        revoke_data_session("u_dg")
        assert _data_grant_allows("u_dg", "sessionA") is False, "撤销后应失效"
    finally:
        bl.unregister_ws_connection("u_dg")


def test_execute_l3_granted_same_session_no_data_block():
    """授权后同一 session 内 L3 不再弹「原始数据」授权(数据层放行)。"""
    bl.unregister_ws_connection("u_g3")
    _conn("u_g3")
    try:
        grant_data_session("u_g3", "sX")
        # 数据层已授权: 不应因「原始数据」挂起; 但站点级(外部)仍可能 pending, 故只断言「无原始数据 reason」
        r = bl.execute("u_g3", "fill", {"text": "项目成本 120 万", **EXT}, timeout=2, session_id="sX")
        if r.get("pending"):
            assert "原始数据" not in r.get("reason", ""), "已授权任务内不应再弹原始数据授权"
        else:
            assert r.get("blocked") is not True
    finally:
        bl.unregister_ws_connection("u_g3")
