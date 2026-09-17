"""V9 本地浏览器 P5 测试: 连接 user_id 不匹配修复(扩展 web_xxx vs Agent user-mtxxx)"""
import json
import sys
import threading
import time

sys.path.insert(0, ".")
import pytest

from core.lib.v8 import browser_local as bl

_IDS = ["web_p5a", "user-mt-p5a", "web_p5b", "user-mt-p5b", "web_p5c", "user-mt-p5c", "web_p5d", "user-mt-p5d"]


def _clean():
    for uid in _IDS:
        bl.unregister_ws_connection(uid)
        bl._browser_pending_ops.pop(uid, None)


def test_mismatch_is_connected():
    """扩展 web_xxx 注册后, Agent user-mtxxx 视角 is_connected 应为 True(任意连接兜底)"""
    _clean()

    class FakeConn:
        def send(self, d):
            pass

    bl.register_ws_connection("web_p5a", FakeConn())
    try:
        assert bl.is_connected("user-mt-p5a"), "Agent id 应视为已连接"
        assert bl.connection_state("user-mt-p5a")["state"] == "connected"
        assert bl.is_connected("web_p5a"), "精确匹配仍有效"
    finally:
        _clean()


def test_mismatch_execute_flow():
    """Agent user-mtxxx 调 execute → 指令发到 web_xxx 连接, 扩展回 result → 正常返回(不再 ConnectionReset)"""
    _clean()

    class FakeConn:
        def __init__(self):
            self.sent = []

        def send(self, d):
            self.sent.append(json.loads(d))

    conn = FakeConn()
    bl.register_ws_connection("web_p5b", conn)
    try:

        def _reply():
            time.sleep(0.3)
            bl._handle_result(
                "web_p5b", conn.sent[0]["cmd_id"], True, {"title": "小红书", "url": "https://www.xiaohongshu.com/note/2"}
            )

        threading.Thread(target=_reply, daemon=True).start()
        r = bl.execute("user-mt-p5b", "navigate", {"url": "https://www.xiaohongshu.com/note/2"}, timeout=5)
        assert r["success"], r
        assert r["data"]["title"] == "小红书"
        assert conn.sent and conn.sent[0]["type"] == "exec" and conn.sent[0]["action"] == "navigate"
    finally:
        _clean()


def test_mismatch_no_connection():
    """无任何连接(精确无 + 兜底无) → 仍返回未连接"""
    _clean()
    r = bl.execute("user-mt-p5c", "navigate", {"url": "https://www.xiaohongshu.com"}, timeout=1)
    assert not r["success"] and "未连接" in r["error"]


def test_mismatch_approval_flow():
    """发布审批跨 id: Agent 挂起 → Agent id 查到 → 审批通过 → 重放执行成功"""
    _clean()

    class FakeConn:
        def __init__(self):
            self.sent = []

        def send(self, d):
            self.sent.append(json.loads(d))

    conn = FakeConn()
    bl.register_ws_connection("web_p5d", conn)
    try:
        r = bl.execute(
            "user-mt-p5d", "publish", {"platform": "xiaohongshu", "title": "测试笔记", "content": "内容"}, timeout=5
        )
        assert r.get("pending") and r.get("op_id"), "发布应挂起待审批: %s" % r
        op = bl.pending_browser_op("user-mt-p5d")
        assert op is not None and op["op_id"] == r["op_id"], "Agent id 应能查到挂起操作"

        def _reply():
            time.sleep(0.3)
            bl._handle_result(
                "web_p5d", conn.sent[0]["cmd_id"], True, {"link": "https://www.xiaohongshu.com/explore/1"}
            )

        threading.Thread(target=_reply, daemon=True).start()
        ra = bl.approve_browser_op("user-mt-p5d", r["op_id"], approve=True)
        assert ra["success"], ra
    finally:
        _clean()


def test_tool_router_dispatch_ctx_user_id():
    """tool_router 分发: browser_local 应走网络工具分支, ctx.user_id 正确传入(不再返回 None 崩 .get())"""
    from core.gateway.tool_router import _execute_sandbox_tool

    _clean()

    class FakeConn:
        def __init__(self):
            self.sent = []

        def send(self, d):
            self.sent.append(json.loads(d))

    conn = FakeConn()
    bl.register_ws_connection("web_p5e", conn)
    try:

        def _reply():
            time.sleep(0.3)
            bl._handle_result(
                "web_p5e", conn.sent[0]["cmd_id"], True, {"title": "小红书", "url": "https://www.xiaohongshu.com/note/p5e"}
            )

        threading.Thread(target=_reply, daemon=True).start()
        r = _execute_sandbox_tool(
            "browser_local",
            {"action": "navigate", "url": "https://www.xiaohongshu.com/note/p5e", "timeout": 8},
            "user-mt-p5e",
            "s_p5e",
        )
        assert isinstance(r, dict), "应返回 dict, 不是 None: %r" % r
        assert r.get("success"), r
        assert conn.sent and conn.sent[0]["action"] == "navigate", "指令应发到扩展连接"
    finally:
        _clean()


def test_tool_router_dispatch_unknown_still_error():
    """未知工具仍返回明确错误(不影响现有分支)"""
    from core.gateway.tool_router import _execute_sandbox_tool

    _clean()
    r = _execute_sandbox_tool("no_such_tool_xyz", {"action": "x"}, "u_p5f", "s_p5f")
    assert isinstance(r, dict) and not r.get("success") and "未知工具" in r.get("error", "")
