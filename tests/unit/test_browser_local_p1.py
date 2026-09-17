"""V9 本地浏览器操作 P1 测试: WS 服务 + 连接管理 + 白名单 + 工具 + 审计"""
import json
import sys
import threading
import time

sys.path.insert(0, ".")
import pytest

from core.lib.v8 import browser_local as bl


def test_whitelist_defaults():
    """默认白名单含小红书/抖音/B站/知乎"""
    wl = bl._whitelist()
    assert "xiaohongshu.com" in wl
    assert "douyin.com" in wl
    assert "bilibili.com" in wl


def test_host_allowed():
    """白名单匹配: 主域/子域放行, 黑名单/未知拒绝"""
    assert bl._host_allowed("www.xiaohongshu.com")
    assert bl._host_allowed("xiaohongshu.com")
    assert bl._host_allowed("www.douyin.com")
    assert not bl._host_allowed("example.com")
    assert not bl._host_allowed("alipay.com")
    assert not bl._host_allowed("")
    assert not bl._host_allowed("evil.com.xiaohongshu.com.evil.io")


def test_conn_registry():
    """连接注册/注销/状态"""
    bl.unregister_ws_connection("u_test1")
    assert not bl.is_connected("u_test1")

    class FakeConn:
        def send(self, d):
            pass

    bl.register_ws_connection("u_test1", FakeConn(), tag="t1")
    assert bl.is_connected("u_test1")
    assert bl.connection_state("u_test1")["state"] == "connected"
    assert bl.unregister_ws_connection("u_test1", reason="tab_closed") is True
    assert not bl.is_connected("u_test1")


def test_execute_not_connected():
    """未连接 → 明确错误"""
    bl.unregister_ws_connection("u_test2")
    r = bl.execute("u_test2", "navigate", {"url": "https://www.xiaohongshu.com"}, timeout=1)
    assert not r["success"]
    assert "未连接" in r["error"]


def test_execute_flow_and_audit(tmp_path):
    """连接 → execute → 扩展回 result → 返回 + 审计落盘"""
    import core.gateway.session_log as sl

    # 用临时 session 日志
    _orig = sl.get_session_log
    _logs = {}

    class FakeLog:
        def __init__(self, sid):
            self.sid = sid
            self.events = []

        def append(self, etype, payload, **kw):
            self.events.append((etype, payload))

    def _fake_get(sid):
        if sid not in _logs:
            _logs[sid] = FakeLog(sid)
        return _logs[sid]

    sl.get_session_log = _fake_get
    try:

        class FakeConn:
            def __init__(self):
                self.sent = []

            def send(self, d):
                self.sent.append(json.loads(d))

        conn = FakeConn()
        bl.register_ws_connection("u_test3", conn, tag="t3")

        # 模拟扩展异步回 result
        def _reply():
            time.sleep(0.3)
            bl._handle_result(
                "u_test3", conn.sent[0]["cmd_id"], True, {"title": "小红书", "url": "https://www.xiaohongshu.com/note/1"}
            )

        threading.Thread(target=_reply, daemon=True).start()
        r = bl.execute(
            "u_test3", "navigate", {"url": "https://www.xiaohongshu.com/note/1"}, timeout=5, session_id="s_test3"
        )
        assert r["success"], r
        assert r["data"]["title"] == "小红书"
        # 审计落盘
        assert any("BROWSER_LOCAL" in p.get("content", "") for _, p in _logs["s_test3"].events), "审计应落盘"
    finally:
        sl.get_session_log = _orig
        bl.unregister_ws_connection("u_test3")


def test_tool_plugin_whitelist_block():
    """工具插件: 白名单外域名拒绝"""
    from core.tools.browser_local import BrowserLocalPlugin

    class Ctx:
        user_id = "u_test4"
        session_id = "s_test4"
        base = None

    p = BrowserLocalPlugin()
    r = p.execute({"action": "navigate", "url": "https://evil.example.com/x"}, Ctx())
    assert not r["success"] and "白名单" in r["error"]


def test_tool_plugin_sensitive_fill_block():
    """工具插件: 敏感 fill(密码)拒绝"""
    from core.tools.browser_local import BrowserLocalPlugin

    class Ctx:
        user_id = "u_test5"
        session_id = "s_test5"
        base = None

    p = BrowserLocalPlugin()
    r = p.execute({"action": "fill", "selector": "#pw", "text": "mypassword123"}, Ctx())
    assert not r["success"] and "禁止" in r["error"]


def test_tool_plugin_not_connected():
    """工具插件: 未连接 → 引导连接"""
    from core.tools.browser_local import BrowserLocalPlugin

    bl.unregister_ws_connection("u_test6")

    class Ctx:
        user_id = "u_test6"
        session_id = "s_test6"
        base = None

    p = BrowserLocalPlugin()
    r = p.execute({"action": "navigate", "url": "https://www.xiaohongshu.com"}, Ctx())
    assert not r["success"] and "未连接" in r["error"]


def test_python_client_preferred_over_extension():
    """适配 Python 客户端: 同 user 已有 python-client 连接时, 扩展重连不覆盖(防「无专属标签页」)"""
    bl.unregister_ws_connection("u_py1")

    class FC:
        def __init__(self):
            self.sent = []

        def send(self, d):
            self.sent.append(json.loads(d))

    py = FC()
    bl.register_ws_connection("u_py1", py, tag="python-client")
    # 扩展(带 tabId)重连同 user → 应被忽略, 保留 python-client
    ext = FC()
    bl.register_ws_connection("u_py1", ext, tag="654919299")
    try:
        r = bl.execute("u_py1", "navigate", {"url": "https://www.xiaohongshu.com/note/1"}, timeout=1)
        # 指令应发到 python-client 连接(而非扩展)
        assert py.sent and not ext.sent, "应保留 python-client 连接执行: py=%d ext=%d" % (len(py.sent), len(ext.sent))
    finally:
        bl.unregister_ws_connection("u_py1")


def test_resolve_any_connection_fallback_python_preferred():
    """连接模型=WS 连接存在即可执行: 无精确匹配时任意连接兜底, 优先 python-client"""
    bl.unregister_ws_connection("web_py2")
    bl.unregister_ws_connection("user-mt-py2")

    class FC:
        def send(self, d):
            pass

    bl.register_ws_connection("web_py2", FC(), tag="12345")  # 扩展
    bl.register_ws_connection("user-mt-py2", FC(), tag="python-client")  # python 客户端
    try:
        assert bl.is_connected("user-mt-py2"), "python 客户端精确匹配"
        assert bl.is_connected("some-other-user"), "任意连接兜底(WS 连接存在即可执行)"
        assert bl._resolve_conn_user("some-other-user") == "user-mt-py2", "多连接兜底应优先 python-client"
    finally:
        bl.unregister_ws_connection("web_py2")
        bl.unregister_ws_connection("user-mt-py2")


def test_handler_login_status_and_verify():
    """_ws_handler_sync 应处理 login_status/verify_required(Python 客户端协议对齐)"""
    import json as _json

    bl.unregister_ws_connection("u_py3")
    msgs = [
        {"type": "hello", "user_id": "u_py3", "tag": "python-client"},
        {"type": "login_status", "platform": "xiaohongshu", "logged_in": True},
        {"type": "verify_required", "platform": "xiaohongshu", "url": "https://www.xiaohongshu.com"},
        {"type": "closed"},
    ]

    class FakeWS:
        def __init__(self, m):
            self.m = list(m)
            self.sent = []

        def __iter__(self):
            while self.m:
                yield _json.dumps(self.m.pop(0))

        def send(self, d):
            self.sent.append(_json.loads(d))

    bl._ws_handler_sync(FakeWS(msgs))
    try:
        st = bl.connection_state("u_py3")
        # closed → 已注销
        assert st is None, "closed 应注销连接"
        # 重新连接验证 state 保存(handler 存活期内检查: 迭代耗尽会 finally 注销)
        import threading as _th

        _evt = _th.Event()

        class FakeWS2:
            def __init__(self, m):
                self.m = list(m)
                self.sent = []

            def __iter__(self):
                for item in self.m:
                    yield _json.dumps(item)
                    if item.get("type") == "verify_required":
                        _evt.set()
                        while _evt.is_set():
                            time.sleep(0.02)  # 忙等主线程 clear(保持连接存活)

            def send(self, d):
                self.sent.append(_json.loads(d))

        msgs2 = [
            {"type": "hello", "user_id": "u_py3", "tag": "python-client"},
            {"type": "login_status", "platform": "douyin", "logged_in": False},
            {"type": "verify_required", "platform": "douyin", "url": "https://www.douyin.com"},
            {"type": "closed"},
        ]
        _th.Thread(target=bl._ws_handler_sync, args=(FakeWS2(msgs2),), daemon=True).start()
        _evt.wait(5)
        st2 = bl.connection_state("u_py3") or {}
        assert st2.get("login_status") == {"douyin": False}, "login_status 应存入连接 state"
        assert st2.get("verify", {}).get("platform") == "douyin", "verify_required 应存入连接 state"
        _evt.clear()  # 放行 handler 继续(closed → 注销)
    finally:
        bl.unregister_ws_connection("u_py3")
