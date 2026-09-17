"""P1 S4: 观察守卫收编测试 — Reminder/Audit/FailurePause(post-execute, 不短路)"""
import os
import sys

sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import pytest

from core.gateway.guards import AuditGuard, FailurePauseGuard, ReminderGuard
from core.os.context import V9Context


@pytest.fixture(autouse=True)
def _fresh_ctx():
    return V9Context()


def _emit(ctx, guard, payload):
    """挂载单守卫并 emit(post-execute 语义), 收集返回"""
    g = guard()
    ctx.mount(g)
    got = []
    ctx.on("_capture", lambda p: got.append(p))
    ctx.emit("tools/post-execute", payload)
    return g, got


# ===== G6 ReminderGuard =====


def test_reminder_never_vetoes(_fresh_ctx):
    """观察永不否决: emit 后 waterfall 不受影响"""
    g, _ = _emit(_fresh_ctx, ReminderGuard, {"tool": "read_file", "args": {"path": "a.py"}, "agent_id": "a1"})
    assert g is not None


def test_reminder_returns_reminder_text(monkeypatch, _fresh_ctx):
    """命中阈值 → payload 带 reminder 文本"""
    from core.gateway import repeat_tool_reminder as rtr

    rtr._counts.clear()
    monkeypatch.setattr(rtr, "observe", lambda aid, tool, args: "[重复提醒] 你已连续 3 次调用同一工具 read_file")
    got = []
    ctx = _fresh_ctx
    ctx.on("tools/post-execute", lambda p: got.append(p))
    g = ReminderGuard()
    ctx.mount(g)
    ctx.emit("tools/post-execute", {"tool": "read_file", "args": {"path": "a.py"}, "agent_id": "a1"})
    reminders = [p.get("guard_results", {}).get("reminder") for p in got]
    assert any("[重复提醒]" in (r or "") for r in reminders), f"应带 reminder: {reminders}"


def test_reminder_no_message_when_ok(monkeypatch, _fresh_ctx):
    """observe 返回 None → 无 reminder"""
    from core.gateway import repeat_tool_reminder as rtr

    monkeypatch.setattr(rtr, "observe", lambda aid, tool, args: None)
    got = []
    ctx = _fresh_ctx
    ctx.on("tools/post-execute", lambda p: got.append(p))
    g = ReminderGuard()
    ctx.mount(g)
    ctx.emit("tools/post-execute", {"tool": "read_file", "args": {}, "agent_id": "a1"})
    assert all("reminder" not in p.get("guard_results", {}) for p in got)


# ===== G15 AuditGuard =====


def test_audit_records_success(monkeypatch, _fresh_ctx):
    """成功工具 → record_tool_flow + audit_tool_call 被调"""
    calls = []

    def fake_flow(tool, args, summary, uid, sid):
        calls.append(("flow", tool, summary))

    def fake_audit(tool, args, result, uid, sid, elapsed_ms=0, round_no=0):
        calls.append(("audit", tool, result.get("success")))

    import core.context.context_manager as cm
    import core.gateway.audit as au

    monkeypatch.setattr(cm, "record_tool_flow", fake_flow)
    monkeypatch.setattr(au, "audit_tool_call", fake_audit)
    g = AuditGuard()
    _fresh_ctx.mount(g)
    _fresh_ctx.emit(
        "tools/post-execute",
        {
            "tool": "read_file",
            "args": {},
            "user_id": "u",
            "session_id": "s",
            "result": {"success": True},
            "elapsed_ms": 5,
        },
    )
    assert ("flow", "read_file", "success (5ms)") in calls
    assert ("audit", "read_file", True) in calls


def test_audit_records_failure(monkeypatch, _fresh_ctx):
    """失败工具 → audit 记失败"""
    calls = []

    def fake_audit(tool, args, result, uid, sid, elapsed_ms=0, round_no=0):
        calls.append(result.get("success"))

    import core.context.context_manager as cm
    import core.gateway.audit as au

    monkeypatch.setattr(cm, "record_tool_flow", lambda *a, **k: None)
    monkeypatch.setattr(au, "audit_tool_call", fake_audit)
    g = AuditGuard()
    _fresh_ctx.mount(g)
    _fresh_ctx.emit(
        "tools/post-execute",
        {
            "tool": "execute_command",
            "args": {},
            "user_id": "u",
            "session_id": "s",
            "result": {"success": False, "error": "boom"},
            "elapsed_ms": 10,
        },
    )
    assert calls == [False]


def test_audit_never_raises(monkeypatch, _fresh_ctx):
    """记录函数抛异常 → 守卫吞掉不阻断"""
    import core.context.context_manager as cm
    import core.gateway.audit as au

    monkeypatch.setattr(cm, "record_tool_flow", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("flow down")))
    monkeypatch.setattr(au, "audit_tool_call", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("audit down")))
    g = AuditGuard()
    _fresh_ctx.mount(g)
    _fresh_ctx.emit(
        "tools/post-execute",
        {
            "tool": "read_file",
            "args": {},
            "user_id": "u",
            "session_id": "s",
            "result": {"success": True},
            "elapsed_ms": 1,
        },
    )  # 不应抛出


# ===== G14 FailurePauseGuard =====


def test_failure_resets_on_success(monkeypatch, _fresh_ctx):
    """成功 → 计数重置, 无暂停"""
    import core.gateway.shared_state as ss

    ss._consecutive_failures["s1"] = 7
    g = FailurePauseGuard()
    _fresh_ctx.mount(g)
    _fresh_ctx.emit(
        "tools/post-execute",
        {
            "tool": "read_file",
            "result": {"success": True},
            "session_id": "s1",
        },
    )
    assert ss._consecutive_failures.get("s1") is None


def test_failure_counts_up(monkeypatch, _fresh_ctx):
    """连续失败递增(与 _check_consecutive_failure 同语义)"""
    import core.gateway.shared_state as ss

    ss._consecutive_failures.pop("s2", None)
    g = FailurePauseGuard()
    _fresh_ctx.mount(g)
    for i in range(2):
        _fresh_ctx.emit(
            "tools/post-execute",
            {
                "tool": "execute_command",
                "result": {"success": False, "error": "e"},
                "session_id": "s2",
            },
        )
    assert ss._consecutive_failures.get("s2") == 2


def test_failure_pause_at_8(monkeypatch, _fresh_ctx):
    """第 8 次失败 → payload 带 paused 断点"""
    import core.gateway.shared_state as ss

    ss._consecutive_failures.pop("s3", None)
    ss._paused_breakpoints.pop("s3", None)
    got = []
    ctx = _fresh_ctx
    ctx.on("tools/post-execute", lambda p: got.append(p))
    g = FailurePauseGuard()
    ctx.mount(g)
    for i in range(8):
        ctx.emit(
            "tools/post-execute",
            {
                "tool": "execute_command",
                "result": {"success": False, "error": f"e{i}"},
                "session_id": "s3",
            },
        )
    last = got[-1]
    gr = last.get("guard_results", {})
    assert gr.get("paused") is True
    assert gr.get("paused_breakpoint", {}).get("reason") == "连续失败8次，任务已暂停"
    assert ss._paused_breakpoints.get("s3", {}).get("count") == 8


def test_failure_hint_at_5(monkeypatch, _fresh_ctx):
    """P4 steer 迁移: guard 不再写 inject_message(≥3 提示由 tool_router 走 steer), 只保留 paused(≥8)"""
    import core.gateway.shared_state as ss

    ss._consecutive_failures.pop("s4", None)
    got = []
    ctx = _fresh_ctx
    ctx.on("tools/post-execute", lambda p: got.append(p))
    g = FailurePauseGuard()
    ctx.mount(g)
    for i in range(5):
        ctx.emit(
            "tools/post-execute",
            {
                "tool": "execute_command",
                "result": {"success": False, "error": "e"},
                "session_id": "s4",
            },
        )
    last = got[-1]
    # P4: ≥3 不再写 inject_message(防与 tool_router steer 双份), 3-7 次无 paused
    assert last.get("guard_results", {}).get("inject_message") is None, "P4 后 guard 不应写 inject_message"
    assert not last.get("guard_results", {}).get("paused"), "5 次失败不应 paused"
    # 8 次才 paused
    for i in range(3):
        ctx.emit(
            "tools/post-execute",
            {
                "tool": "execute_command",
                "result": {"success": False, "error": "e"},
                "session_id": "s4",
            },
        )
    last8 = got[-1]
    assert last8.get("guard_results", {}).get("paused"), "8 次失败应 paused"
