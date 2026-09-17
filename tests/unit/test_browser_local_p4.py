"""V9 本地浏览器 P4 测试: monitor + 定时 + 回复队列"""
import json
import sys
import tempfile
import threading
import time

sys.path.insert(0, ".")
import pytest

from core.lib.v8 import browser_local as bl


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(bl, "_REPLY_HISTORY_DIR", str(tmp_path / "reply_history"))
    monkeypatch.setattr(bl, "_MONITOR_JOBS", {})
    monkeypatch.setattr(bl, "_REPLY_QUEUE", {})
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


def test_monitor_start_requires_connection():
    """未连接 → monitor_start 拒绝"""
    bl.unregister_ws_connection("u_p4a")
    r = bl.monitor_start("u_p4a", "xiaohongshu", "考研", interval=60)
    assert not r["success"] and "未连接" in r["error"]


def test_monitor_start_snapshot():
    """连接后 monitor_start → 记录初始快照 + 任务注册"""
    bl.unregister_ws_connection("u_p4b")
    conn = _conn("u_p4b")

    # 初始 extract 返回
    def _reply():
        time.sleep(0.2)
        bl._handle_result("u_p4b", conn.sent[-1]["cmd_id"], True, {"content": "初始内容"})

    threading.Thread(target=_reply, daemon=True).start()
    r = bl.monitor_start(
        "u_p4b", "xiaohongshu", "考研", interval=60, url="https://www.xiaohongshu.com/search_result?keyword=x"
    )
    assert r["success"], r
    jobs = bl.list_monitor_jobs("u_p4b")
    assert len(jobs) == 1 and jobs[0]["target"] == "考研"
    assert jobs[0]["status"] == "running"
    bl.unregister_ws_connection("u_p4b")


def test_monitor_change_detected():
    """内容变化 → _monitor_check 返回 changed + 计数"""
    bl.unregister_ws_connection("u_p4c")
    conn = _conn("u_p4c")

    # 初始快照
    def _reply1():
        time.sleep(0.2)
        bl._handle_result("u_p4c", conn.sent[-1]["cmd_id"], True, {"content": "旧内容"})

    threading.Thread(target=_reply1, daemon=True).start()
    r = bl.monitor_start("u_p4c", "xiaohongshu", "话题A", interval=60)
    assert r["success"]

    # 变化: 新 extract 返回不同内容
    def _reply2():
        time.sleep(0.2)
        bl._handle_result("u_p4c", conn.sent[-1]["cmd_id"], True, {"content": "新内容来了!"})

    threading.Thread(target=_reply2, daemon=True).start()
    jobs = bl.list_monitor_jobs("u_p4c")
    res = bl._monitor_check(jobs[0])
    assert res["changed"] is True, res
    jobs2 = bl.list_monitor_jobs("u_p4c")
    assert jobs2[0]["changes"] == 1
    bl.unregister_ws_connection("u_p4c")


def test_reply_queue_enqueue_list():
    """监控到新内容 → enqueue_reply → 队列出现待处理项"""
    bl.unregister_ws_connection("u_p4d")
    r = bl.enqueue_reply("u_p4d", {"platform": "xiaohongshu", "target": "考研", "comment": "请问真题在哪买"}, "您好，真题在商品页有售～")
    assert r["success"] and r["reply_id"]
    q = bl.list_reply_queue("u_p4d", status="pending")
    assert len(q) == 1 and q[0]["status"] == "pending"
    assert "真题" in q[0]["suggested_reply"]


def test_reply_approve_executes_and_history():
    """审批回复 → 执行(fill+click) + 回复历史落盘"""
    bl.unregister_ws_connection("u_p4e")
    conn = _conn("u_p4e")
    r = bl.enqueue_reply(
        "u_p4e",
        {
            "platform": "xiaohongshu",
            "target": "考研",
            "comment": "请问怎么联系",
            "reply_selector": "textarea",
            "send_selector": "button",
        },
        "您好，可私信联系～",
    )
    q = bl.list_reply_queue("u_p4e", status="pending")
    rid = q[0]["id"]

    # fill → success; click → success(顺序回两个 cmd)
    def _reply_both():
        # 等 fill 指令发出
        for _ in range(50):
            with bl._browser_lock:
                _cmds = [s.get("cmd_id") for s in conn.sent if s.get("type") == "exec"]
            if len(_cmds) >= 1:
                bl._handle_result("u_p4e", _cmds[0], True, {"filled": True})
                break
            time.sleep(0.1)
        # 等 click 指令发出
        for _ in range(50):
            with bl._browser_lock:
                _cmds = [s.get("cmd_id") for s in conn.sent if s.get("type") == "exec"]
            if len(_cmds) >= 2:
                bl._handle_result("u_p4e", _cmds[1], True, {"clicked": True})
                break
            time.sleep(0.1)

    threading.Thread(target=_reply_both, daemon=True).start()
    ra = bl.approve_reply("u_p4e", rid, approve=True)
    assert ra.get("success"), ra
    assert ra.get("status") == "reply_executed"
    hist = bl.list_reply_history("u_p4e")
    assert hist and hist[0]["success"] is True
    assert "私信" in hist[0]["text"]
    # 队列状态更新
    q2 = bl.list_reply_queue("u_p4e")
    assert q2[0]["status"] == "approved"
    bl.unregister_ws_connection("u_p4e")


def test_reply_reject():
    """拒绝回复 → 不执行, 标记 rejected"""
    bl.unregister_ws_connection("u_p4f")
    bl.enqueue_reply("u_p4f", {"platform": "douyin", "target": "t"}, "建议回复")
    q = bl.list_reply_queue("u_p4f", status="pending")
    ra = bl.approve_reply("u_p4f", q[0]["id"], approve=False)
    assert ra.get("status") == "reply_rejected"
    q2 = bl.list_reply_queue("u_p4f")
    assert q2[0]["status"] == "rejected"


def test_gateway_routes():
    """网关: monitor 查询(路由层) + approve_reply 回执(编排层)"""
    src = open("routes/browser.py", encoding="utf-8").read()
    assert '"/v9/browser/monitor"' in src
    gw = open("core/gateway/approval.py", encoding="utf-8").read()  # P3-A: _v9_handle_approvals 已归位
    assert 'data.get("approve_reply")' in gw
    assert "approve_reply(user_id, _rp_approve" in gw


def test_tool_plugin_p4_actions():
    """工具插件: monitor_start/reply_enqueue 动作"""
    from core.tools.browser_local import BrowserLocalPlugin

    bl.unregister_ws_connection("u_p4h")
    _conn("u_p4h")

    class Ctx:
        user_id = "u_p4h"
        session_id = "s_p4h"
        base = None

    p = BrowserLocalPlugin()
    # reply_enqueue 无需连接? 需要(内部直接 enqueue)
    r = p.execute({"action": "reply_enqueue", "item": {"target": "x"}, "suggested_reply": "回复"}, Ctx())
    assert r["success"] and r["reply_id"], r
    # monitor_start 需连接
    r2 = p.execute({"action": "monitor_start", "platform": "xiaohongshu", "target": "考研", "interval": 30}, Ctx())
    assert r2["success"], r2
    bl.unregister_ws_connection("u_p4h")


def test_frontend_ops_panel():
    """前端: 运营面板 + 回复审批"""
    html = open("web/dashboard/workbench.html", encoding="utf-8").read()
    assert "opsPanel" in html and "loadOpsPanel" in html
    assert "opsReplyApprove" in html
    assert "approve_reply" in html, "前端应带 approve_reply 审批"
