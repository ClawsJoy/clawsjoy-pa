"""#8 审计告警主动通知回归测试: notify_boss 落盘+SSE + turn_end/预算触发 + 前端"""
import json
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _iso(monkeypatch, tmp_path):
    """隔离: notifications 文件路径(env PROJECT_ROOT) + session_log 注册表 + ledger"""
    import core.gateway.sandbox_util as su
    import core.gateway.session_log as sl
    import core.lib.v8.notifications as nf

    # 不动 PROJECT_ROOT(agent_gateway 模块导入读 config 依赖真实根); notify_boss 输出路径隔离
    monkeypatch.setattr(su, "_NOTIFY_OUTPUT_PATH", str(tmp_path / "data" / "v8" / "notifications.json"))
    monkeypatch.setattr(nf, "_NOTIFICATIONS_PATH", str(tmp_path / "data" / "v8" / "notifications.json"))
    monkeypatch.setattr(nf, "_READ_PATH", str(tmp_path / "data" / "v8" / "notifications_read.json"))
    monkeypatch.setattr(nf, "_sse_subscribers", [])
    monkeypatch.setattr(sl, "_logs", {})
    _orig = sl.get_session_log

    def _get_iso(sid, base_dir=None):
        return _orig(sid, base_dir=tmp_path)

    monkeypatch.setattr(sl, "get_session_log", _get_iso)
    # ledger 落盘无关测试 → no-op
    import core.lib.v8.ledger as ld

    monkeypatch.setattr(ld.ledger, "record_event", lambda **kw: {})
    yield tmp_path


def test_notify_boss_writes_and_broadcasts(tmp_path):
    """notify_boss(event_type, message, detail): 落盘 + SSE 广播"""
    from core.gateway.sandbox_util import notify_boss
    from core.lib.v8.notifications import list_notifications, subscribe_sse

    q, unsub = subscribe_sse()
    notify_boss(
        event_type="turn_end",
        message="V9 任务回合异常: blocked — 写操作等待确认",
        detail="turn_id=42 tools=3 tokens=100 session=s1",
        level="warn",
    )
    # 落盘 + 归一化带 event_type/detail
    res = list_notifications()
    assert res["total"] == 1
    it = res["items"][0]
    assert it["event_type"] == "turn_end" and "blocked" in it["message"]
    assert it["detail"] and it["level"] == "warn" and it["read"] is False
    # SSE 广播送达
    got = q.get_nowait()
    assert got["event_type"] == "turn_end" and got["id"] == it["id"]
    unsub()


def test_notify_boss_legacy_compat(tmp_path):
    """旧调用兼容: notify_boss(message, level, extra) 仍工作"""
    from core.gateway.sandbox_util import notify_boss
    from core.lib.v8.notifications import list_notifications

    notify_boss("沙箱越权拦截", "error", {"path": "/etc/passwd"})
    res = list_notifications()
    it = res["items"][0]
    assert it["message"] == "沙箱越权拦截" and it["level"] == "error"
    assert it["event_type"] == "general" and it["extra"].get("path") == "/etc/passwd"


def test_turn_end_triggers_notification(tmp_path):
    """turn_end reason=error/blocked/cancelled → 通知; completed → 不通知"""
    import agent_gateway_enhanced as main
    from core.lib.v8.notifications import list_notifications

    main._write_turn_end("s_n1", 1, 100, "blocked", "写操作等待老板确认", 2)
    main._write_turn_end("s_n1", 2, 50, "completed", "正常完成", 3)
    res = list_notifications()
    assert res["total"] == 1, f"只有 blocked 应触发: {res['total']}"
    assert res["items"][0]["event_type"] == "turn_end" and "blocked" in res["items"][0]["message"]
    main._write_turn_end("s_n1", 3, 10, "cancelled", "协作取消", 0)
    main._write_turn_end("s_n1", 4, 10, "error", "API错误", 0)
    assert list_notifications()["total"] == 3, "cancelled/error 也应触发"


def test_budget_overrun_trigger_source():
    """预算超限 → notify_boss(event_type=budget_limit)"""
    src = open("agent_gateway_enhanced.py", encoding="utf-8").read()
    assert 'event_type="budget_limit"' in src
    assert "V9 工具预算超限" in src


def test_exec_path_trigger_source():
    """exec 路径 turn_end 异常也触发通知"""
    src = open("core/gateway/execute_agent_task.py", encoding="utf-8").read()
    assert 'event_type="turn_end"' in src
    assert 'if _reason in ("error", "blocked", "cancelled")' in src


def test_sse_endpoint_registered():
    """SSE 路由注册 + subscribe_sse/broadcast 存在"""
    src = open("core/lib/v8/routes/v8_misc.py", encoding="utf-8").read()
    assert '"/v8/notifications/stream"' in src
    assert "subscribe_sse" in src and "text/event-stream" in src
    nf = open("core/lib/v8/notifications.py", encoding="utf-8").read()
    assert "def subscribe_sse" in nf and "def broadcast_notification" in nf


def test_frontend_realtime(tmp_path):
    """前端: EventSource 订阅 + 轮询 5s"""
    # 模块化拆分后通知逻辑在 notifications.js
    src = open("web/static/js/notifications.js", encoding="utf-8").read()
    assert "EventSource" in src and "/v8/notifications/stream" in src
    assert "setInterval(pollNotifications, 5000)" in src, "轮询应缩短到 5s"
    assert "if (notifShown) loadNotifList()" in src, "SSE 新通知应实时刷新列表"
