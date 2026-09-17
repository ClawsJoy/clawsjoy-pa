"""V9 本地浏览器 P2 测试: click/fill/search + 审批流程"""
import json
import sys
import threading
import time

sys.path.insert(0, ".")
import pytest

from core.lib.v8 import browser_local as bl


def test_sensitive_click_detection():
    """发布/提交按钮 click → 需审批"""
    assert bl._needs_approval("click", {"selector": "#publish-btn"})
    assert bl._needs_approval("click", {"selector": "button.submit"})
    assert bl._needs_approval("click", {"selector": "发布"})
    assert bl._needs_approval("click", {"selector": ".note-card"}) is None, "普通卡片点击不需审批"


def test_sensitive_fill_detection():
    """敏感表单 fill(密码/支付) → 需审批"""
    assert bl._needs_approval("fill", {"selector": "#password", "text": "x"})
    assert bl._needs_approval("fill", {"selector": "#pay", "text": "y"})
    assert bl._needs_approval("fill", {"selector": "#search-input", "text": "考研"}) is None, "搜索框填词不需审批"


def test_pending_parked_when_sensitive():
    """敏感操作 → 挂起 pending 等确认, 不直接执行"""
    bl.unregister_ws_connection("u_p2a")

    class FakeConn:
        def __init__(self):
            self.sent = []

        def send(self, d):
            self.sent.append(json.loads(d))

    bl.register_ws_connection("u_p2a", FakeConn())
    r = bl.execute("u_p2a", "click", {"selector": "#publish-btn"}, timeout=2)
    assert not r["success"] and r.get("pending"), r
    assert "需要确认" in r.get("error", "")
    # 未发送指令给扩展(挂起)
    assert bl.pending_browser_op("u_p2a") is not None
    bl.unregister_ws_connection("u_p2a")


def test_auto_execute_search_and_fill():
    """search/fill(非敏感)直接执行, 不挂起"""
    bl.unregister_ws_connection("u_p2b")

    class FakeConn:
        def __init__(self):
            self.sent = []

        def send(self, d):
            self.sent.append(json.loads(d))

    conn = FakeConn()
    bl.register_ws_connection("u_p2b", conn)

    # fill 搜索框 → 直接发送
    def _reply():
        time.sleep(0.3)
        bl._handle_result("u_p2b", conn.sent[-1]["cmd_id"], True, {"filled": True})

    threading.Thread(target=_reply, daemon=True).start()
    r = bl.execute("u_p2b", "fill", {"selector": "#search-input", "text": "考研"}, timeout=5, session_id="s_p2b")
    assert r["success"], r
    assert bl.pending_browser_op("u_p2b") is None, "非敏感 fill 不应挂起"
    bl.unregister_ws_connection("u_p2b")


def test_approve_flow_replays():
    """审批通过 → 重放执行; 拒绝 → 停止"""
    bl.unregister_ws_connection("u_p2c")

    class FakeConn:
        def __init__(self):
            self.sent = []

        def send(self, d):
            self.sent.append(json.loads(d))

    conn = FakeConn()
    bl.register_ws_connection("u_p2c", conn)
    # 挂起敏感 click
    r1 = bl.execute("u_p2c", "click", {"selector": "#publish-btn"}, timeout=2)
    op = bl.pending_browser_op("u_p2c")
    assert op is not None
    # 拒绝 → 不执行
    rr = bl.approve_browser_op("u_p2c", op["op_id"], approve=False)
    assert rr.get("status") == "browser_rejected"
    assert bl.pending_browser_op("u_p2c") is None
    # 重新挂起 → 通过 → 重放执行
    r2 = bl.execute("u_p2c", "click", {"selector": "#publish-btn"}, timeout=2)
    op2 = bl.pending_browser_op("u_p2c")

    def _reply2():
        time.sleep(0.3)
        bl._handle_result("u_p2c", conn.sent[-1]["cmd_id"], True, {"clicked": True})

    threading.Thread(target=_reply2, daemon=True).start()
    ra = bl.approve_browser_op("u_p2c", op2["op_id"], approve=True)
    assert ra.get("success"), ra
    assert (ra.get("data") or {}).get("clicked") is True
    bl.unregister_ws_connection("u_p2c")


def test_tool_plugin_pending_passthrough():
    """工具插件: 敏感 fill 返回 pending + op_id(已连接场景)"""
    from core.tools.browser_local import BrowserLocalPlugin

    bl.unregister_ws_connection("u_p2d")

    class FakeConn:
        def send(self, d):
            pass

    bl.register_ws_connection("u_p2d", FakeConn())

    class Ctx:
        user_id = "u_p2d"
        session_id = "s_p2d"
        base = None

    p = BrowserLocalPlugin()
    r = p.execute({"action": "fill", "selector": "#pay-amount", "text": "100"}, Ctx())
    assert r.get("pending") and r.get("op_id"), r
    assert bl.pending_browser_op("u_p2d") is not None
    bl.unregister_ws_connection("u_p2d")


def test_frontend_approval_card():
    """前端: 审批卡渲染 + 状态提示"""
    app = open("web/static/js/approval.js", encoding="utf-8").read()
    chat = open("web/static/js/chat.js", encoding="utf-8").read()
    assert "renderBrowserConfirmCard" in app
    assert "sendBrowserApproval" in app
    assert "global.renderBrowserConfirmCard" in app
    assert "approve_browser" in app, "审批请求应带 approve_browser"
    assert "result.pending" in chat, "chat.js 应检测 pending"
    assert "renderBrowserConfirmCard" in chat, "chat.js 应渲染审批卡"
    assert "正在操作本地浏览器" in chat, "应有实时状态提示"


def test_gateway_approval_route():
    """网关: approve_browser 回执分发"""
    src = open("core/gateway/approval.py", encoding="utf-8").read()  # P3-A: _v9_handle_approvals 已归位
    assert 'data.get("approve_browser")' in src
    assert "browser_confirmed" in src
    assert "browser_rejected" in src
