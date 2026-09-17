"""V9 本地浏览器 P3 测试: publish + 发布审批 + 发布历史 + 审计 + 扩展(合并后)"""
import json
import sys
import tempfile
import threading
import time

sys.path.insert(0, ".")
import pytest

from core.lib.v8 import browser_local as bl


@pytest.fixture(autouse=True)
def _tmp_history(monkeypatch, tmp_path):
    """隔离发布历史目录"""
    monkeypatch.setattr(bl, "_PUBLISH_HISTORY_DIR", str(tmp_path / "publish_history"))
    yield


def _conn(u):
    class FakeConn:
        def __init__(self):
            self.sent = []

        def send(self, d):
            self.sent.append(json.loads(d))

    c = FakeConn()
    bl.register_ws_connection(u, c)
    return c


def test_publish_forced_approval():
    """publish 强制逐篇审批(即使内容正常)"""
    bl.unregister_ws_connection("u_p3a")
    _conn("u_p3a")
    r = bl.execute(
        "u_p3a", "publish", {"platform": "xiaohongshu", "title": "考研笔记", "content": "正文", "tags": ["考研"]}, timeout=2
    )
    assert not r["success"] and r.get("pending"), r
    assert "逐篇确认" in r.get("error", "")
    assert bl.pending_browser_op("u_p3a") is not None
    op = bl.pending_browser_op("u_p3a")
    assert op["params"]["title"] == "考研笔记"
    bl.unregister_ws_connection("u_p3a")


def test_publish_approve_executes_and_records():
    """审批通过 → 执行 → 发布历史落盘(含平台链接)"""
    bl.unregister_ws_connection("u_p3b")
    conn = _conn("u_p3b")
    r1 = bl.execute(
        "u_p3b", "publish", {"platform": "xiaohongshu", "title": "考研数学", "content": "公式总结", "tags": ["数学"]}, timeout=2
    )
    op = bl.pending_browser_op("u_p3b")

    def _reply():
        time.sleep(0.3)
        bl._handle_result(
            "u_p3b",
            conn.sent[-1]["cmd_id"],
            True,
            {"publish_clicked": True, "link": "https://www.xiaohongshu.com/note/abc123"},
        )

    threading.Thread(target=_reply, daemon=True).start()
    ra = bl.approve_browser_op("u_p3b", op["op_id"], approve=True)
    assert ra.get("success"), ra
    assert (ra.get("data") or {}).get("publish_clicked") is True
    hist = bl.list_publish_history("u_p3b")
    assert hist, "应有发布历史"
    assert hist[0]["platform"] == "xiaohongshu"
    assert "abc123" in hist[0].get("link", "")
    assert hist[0]["success"] is True
    assert "考研数学" in hist[0]["content_summary"]
    bl.unregister_ws_connection("u_p3b")


def test_publish_failure_records_error():
    """发布失败 → 历史记录错误原因"""
    bl.unregister_ws_connection("u_p3c")
    conn = _conn("u_p3c")
    r1 = bl.execute("u_p3c", "publish", {"platform": "douyin", "title": "视频", "content": "内容"}, timeout=2)
    op = bl.pending_browser_op("u_p3c")

    def _reply():
        time.sleep(0.3)
        bl._handle_result("u_p3c", conn.sent[-1]["cmd_id"], False, {"error": "登录态失效, 无法发布"})

    threading.Thread(target=_reply, daemon=True).start()
    ra = bl.approve_browser_op("u_p3c", op["op_id"], approve=True)
    assert not ra.get("success"), ra
    hist = bl.list_publish_history("u_p3c")
    assert hist and hist[0]["success"] is False
    assert "登录态失效" in hist[0]["error"]
    bl.unregister_ws_connection("u_p3c")


def test_publish_history_route():
    """网关: /v9/browser/publish_history 路由存在(已迁 routes/browser.py Blueprint)"""
    src = open("routes/browser.py", encoding="utf-8").read()
    assert '"/v9/browser/publish_history"' in src
    assert "list_publish_history" in src


def test_tool_plugin_publish_pending():
    """工具插件: publish 返回 pending + 完整参数"""
    from core.tools.browser_local import BrowserLocalPlugin

    bl.unregister_ws_connection("u_p3e")
    _conn("u_p3e")

    class Ctx:
        user_id = "u_p3e"
        session_id = "s_p3e"
        base = None

    p = BrowserLocalPlugin()
    r = p.execute(
        {"action": "publish", "platform": "xiaohongshu", "title": "标题", "content": "正文", "tags": ["a"]}, Ctx()
    )
    assert r.get("pending") and r["params"]["title"] == "标题"
    bl.unregister_ws_connection("u_p3e")


def test_frontend_publish_card():
    """前端: 发布审批卡展示完整内容"""
    app = open("web/static/js/approval.js", encoding="utf-8").read()
    assert "op.action === 'publish'" in app
    assert "平台: " in app and "标题: " in app and "正文: " in app and "标签: " in app
    assert "将在你的真实账号发布" in app, "应有发布风险提示"


@pytest.mark.skip(reason="扩展已退役(移 archive)，测试已失效")
def test_manifest_no_browser_permissions():
    """插件不再连 WS/CDP: manifest 不应含 debugger/tabs/alarms(这些在 Python 客户端侧)"""
    import json as _json

    _m = _json.load(open("clawsjoy-ai-extension/manifest.json", encoding="utf-8"))
    assert "debugger" not in _m["permissions"], "CDP 已移到 Python 客户端, 插件不需要 debugger"
    assert "tabs" not in _m["permissions"], "插件不再管理标签页"
    assert "alarms" not in _m["permissions"], "插件不再有 WS keepalive"
    assert {"sidePanel", "storage", "downloads"} <= set(_m["permissions"]), "保留工作台/存储/下载权限"


@pytest.mark.skip(reason="扩展已退役(移 archive)，测试已失效")
def test_plugin_no_active_ws():
    """插件不主动连 WS: background.ts 不应有 WebSocket/keepalive/debugger(桥接已移除)"""
    _bg = open("clawsjoy-ai-extension/src/background.ts", encoding="utf-8").read()
    assert "new WebSocket" not in _bg, "插件不应建 WS 连接"
    assert "KEEPALIVE_ALARM" not in _bg, "插件不应有 keepalive alarm"
    assert "chrome.debugger" not in _bg, "插件不应有 CDP"
    assert "Python 客户端" in _bg or "python-client" in _bg, "插件状态显示应提及 Python 客户端"


@pytest.mark.skip(reason="扩展已退役(移 archive)，测试已失效")
def test_plugin_status_via_http():
    """插件状态来源: 轮询 V9 /v9/browser/status(HTTP), 不连 WS"""
    _bg = open("clawsjoy-ai-extension/src/background.ts", encoding="utf-8").read()
    assert "/v9/browser/status" in _bg, "应轮询 /v9/browser/status"
    assert "fetch(" in _bg, "应通过 fetch 拉状态"
    assert "apiBase" in _bg, "状态请求应带 apiBase(设置里的后端地址)"


def test_gateway_browser_status_route():
    """V9 后端应有 /v9/browser/status 路由(get_connection_info)"""
    _gw = open("routes/browser.py", encoding="utf-8").read()
    assert '"/v9/browser/status"' in _gw, "网关应有状态路由(已迁 routes/browser.py)"
    assert "get_connection_info" in _gw, "路由应调 get_connection_info"
    _bl = open("core/lib/v8/browser_local.py", encoding="utf-8").read()
    assert "def get_connection_info" in _bl, "browser_local 应有连接信息查询"
    assert "python-client" in _bl.split("def get_connection_info")[1], "状态应标识 python-client"


def test_agent_client_is_executor():
    """Python 客户端(scripts/agent_client)是唯一执行者: 文件齐全 + 关键行为"""
    import os

    for f in ("agent_client.py", "ws_client.py", "browser.py", "actions.py", "platforms.py"):
        assert os.path.exists(os.path.join("scripts/agent_client", f)), "缺 %s" % f
    _ws = open("scripts/agent_client/ws_client.py", encoding="utf-8").read()
    assert "重连" in _ws and "hello" in _ws, "ws_client 应有重连 + hello 注册"
    _ac = open("scripts/agent_client/actions.py", encoding="utf-8").read()
    for a in ("def search", "def publish", "def extract", "def navigate"):
        assert a in _ac, "actions 应含 %s" % a
    _br = open("scripts/agent_client/browser.py", encoding="utf-8").read()
    assert "detect_verify" in _br, "browser 应有风控检测"
    _y = open("scripts/agent_client/config/platforms.yaml", encoding="utf-8").read()
    assert "xiaohongshu" in _y or "xiaohongshu" in open("scripts/agent_client/platforms.py", encoding="utf-8").read()
    _pl = open("scripts/agent_client/platforms.py", encoding="utf-8").read()
    assert "youtube" in _pl, "平台配置应含 youtube"
    assert "ytd-video-renderer" in _pl, "youtube 卡片选择器应为 ytd-video-renderer"
    assert "search_requires_login" in _pl, "应支持 search_requires_login(YouTube 搜索匿名可用)"


@pytest.mark.skip(reason="扩展已退役(移 archive)，测试已失效")
def test_sidebar_status_display():
    """插件设置显示客户端状态(✅/❌ + 启动指引), 不再有授权开关"""
    _html = open("clawsjoy-ai-extension/src/sidebar/index.html", encoding="utf-8").read()
    _ts = open("clawsjoy-ai-extension/src/sidebar/index.ts", encoding="utf-8").read()
    assert "Python 客户端已连接" in _ts, "应有已连接文案(动态生成, 在 index.ts)"
    assert "未检测到客户端" in _html or "未检测到客户端" in _ts, "应有未检测文案"
    assert "agent_client.py" in _html, "应有启动客户端指引"
    assert "browserStatus" in _ts, "index.ts 应轮询状态"
    assert "browserConnect" not in _ts, "不应再有授权连接开关"
    assert "setBrowserEnabled" not in _html, "不应再有 checkbox 开关"


def test_system_prompt_prefers_browser_local():
    """问题4: 系统提示应引导 Agent 优先 browser_local, 不写临时 python 脚本抓取"""
    _sys = open("config/prompts/agent_system.md", encoding="utf-8").read()
    assert "本地浏览器操作（browser_local 优先）" in _sys, "系统提示应有 browser_local 优先引导"
    assert "禁止为抓取网页而写临时 python 脚本" in _sys, "应明确禁止临时脚本抓取"
    assert "浏览器操作统一走 browser_local" in _sys, "应引导统一走 browser_local"
