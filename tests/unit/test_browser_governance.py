# -*- coding: utf-8 -*-
"""浏览器治理门测试（2026-09-10）: 在场授权 / 一次通过(会话级) / 随时停止"""
import sys

sys.path.insert(0, ".")
import pytest

from core.lib.v8 import browser_local as BL

U = "test_user_gate"


def setup_function(_fn):
    BL.revoke_browser_session(U)
    BL.resume_browser_session(U)


def test_gate_state_consistent_across_conn_user_resolution():
    """回归(2026-09-10): 写方按键解析后写入、读方按原键查询 → 治理态静默不一致。

    场景: 有连接注册时 _resolve_conn_user(raw) 可能返回另一个 id(扩展 web_xxx / 兜底解析)。
    要求 raw 键写入的 grant/stop 在 raw 键查询时命中, 且不得因锁内解析而死锁。
    """

    class _Conn:
        def send(self, d):
            pass

    BL.register_ws_connection("web_gate_regress", _Conn())
    try:
        BL.stop_browser_session(U, "回归停止")
        assert BL._stop_reason(U) == "回归停止", "stop 写入后按原键读不到(键不对称)"
        assert BL.session_gate(U)["stopped"] is True
        BL.grant_browser_session(U, hosts=["chat.deepseek.com"], actions=["navigate"], ttl_s=600)
        assert BL._grant_allows(U, "navigate", {"url": "https://chat.deepseek.com/x"}), "grant 写入后按原键读不到"
        assert BL.session_gate(U)["granted"] is True
        BL.revoke_browser_session(U)
        assert not BL._grant_allows(U, "navigate", {"url": "https://chat.deepseek.com/x"})
    finally:
        BL.unregister_ws_connection("web_gate_regress")
        BL.revoke_browser_session(U)
        BL.resume_browser_session(U)


def test_external_host_detection():
    assert BL._is_external_host("chat.deepseek.com")
    assert BL._is_external_host("deepseek.com")
    assert not BL._is_external_host("www.xiaohongshu.com")
    assert not BL._is_external_host("")


def test_external_action_needs_approval():
    r = BL._needs_approval("navigate", {"url": "https://chat.deepseek.com/a/chat/s/abc"})
    assert r and "外部站点" in r


def test_platform_action_no_external_approval():
    r = BL._needs_approval("navigate", {"url": "https://www.xiaohongshu.com"})
    assert not r


def test_grant_allows_same_host():
    assert not BL._grant_allows(U, "navigate", {"url": "https://chat.deepseek.com/x"})
    BL.grant_browser_session(U, hosts=["chat.deepseek.com"], actions=["navigate", "fill"], ttl_s=600)
    assert BL._grant_allows(U, "navigate", {"url": "https://chat.deepseek.com/x"})
    assert BL._grant_allows(U, "fill", {})  # 无 url 时按当前页面(未知)→ 放行
    assert not BL._grant_allows(U, "publish", {})  # 未授权动作仍拦


def test_grant_expiry():
    BL.grant_browser_session(U, hosts=["chat.deepseek.com"], actions=["navigate"], ttl_s=-1)
    assert not BL._grant_allows(U, "navigate", {"url": "https://chat.deepseek.com/x"})


def test_grant_other_host_blocked():
    BL.grant_browser_session(U, hosts=["chat.deepseek.com"], actions=["navigate"], ttl_s=600)
    assert not BL._grant_allows(U, "navigate", {"url": "https://example.com/x"})


def test_stop_and_resume():
    assert BL._stop_reason(U) is None
    BL.stop_browser_session(U, "老板手动停止")
    assert BL._stop_reason(U) == "老板手动停止"
    BL.resume_browser_session(U)
    assert BL._stop_reason(U) is None


def test_grant_clears_stop():
    BL.stop_browser_session(U, "停")
    BL.grant_browser_session(U, hosts=["chat.deepseek.com"], ttl_s=60)
    assert BL._stop_reason(U) is None


def test_session_gate_shape():
    BL.stop_browser_session(U, "停一下")
    g = BL.session_gate(U)
    assert g["stopped"] and g["stop_reason"] == "停一下"
    BL.resume_browser_session(U)
    BL.grant_browser_session(U, hosts=["chat.deepseek.com"], ttl_s=120)
    g2 = BL.session_gate(U)
    assert g2["granted"] and g2["grant_expires_in"] > 0 and "chat.deepseek.com" in g2["grant_hosts"]


def test_revoke():
    BL.grant_browser_session(U, ttl_s=600)
    assert BL.session_gate(U)["granted"]
    BL.revoke_browser_session(U)
    assert not BL.session_gate(U)["granted"]
