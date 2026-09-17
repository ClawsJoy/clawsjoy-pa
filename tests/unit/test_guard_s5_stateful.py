"""P1 S5: 状态机守卫收编测试 — Approval/Plan/Recursion(检测收编, 状态动作留调用方)"""
import os
import sys

sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")

import pytest

from core.gateway.guards import ApprovalGuard, PlanGuard, RecursionGuard
from core.os.context import V9Context


@pytest.fixture(autouse=True)
def _fresh_ctx():
    return V9Context()


@pytest.fixture(autouse=True)
def _clean_recursion(monkeypatch):
    import core.gateway.execute_agent_task as eat
    import core.gateway.shared_state as ss

    # 清空实际 dict(而非替换): check_recursion 绑定 eat._recursion_tracker,
    # 测试内修改必须作用到该 dict; teardown 无需恢复(全量测试亦受益于清空)
    eat._recursion_tracker.clear()
    ss._recursion_tracker.clear()
    yield
    eat._recursion_tracker.clear()
    ss._recursion_tracker.clear()


def _run(ctx, guard, payload):
    g = guard()
    ctx.mount(g)
    return ctx.waterfall("tools/pre-execute", payload)


# ===== G1 ApprovalGuard =====


def test_approval_passes_non_write(_fresh_ctx):
    """非写工具不触发审批"""
    r = _run(_fresh_ctx, ApprovalGuard, {"tool": "read_file", "session_id": "s"})
    assert r is None


def test_approval_pending_unconfirmed(_fresh_ctx):
    """写工具未确认 → write_pending"""
    r = _run(
        _fresh_ctx,
        ApprovalGuard,
        {
            "tool": "write_file",
            "session_id": "s",
            "tool_call_id": "call_1",
            "args": {"path": "a.py", "content": "x"},
            "approved": {},
        },
    )
    assert r is not None and r["status"] == "write_pending"
    assert r["pending_id"] == "call_1"
    assert r["pending_write"]["path"] == "a.py"
    assert r["pending_write"]["approved"] is False
    assert r["error"]["pending"] is True


def test_approval_passes_approved_matching(_fresh_ctx):
    """已确认且 id 匹配 → 放行"""
    r = _run(
        _fresh_ctx,
        ApprovalGuard,
        {
            "tool": "write_file",
            "session_id": "s",
            "tool_call_id": "call_1",
            "args": {"path": "a.py"},
            "approved": {"id": "call_1", "approved": True},
        },
    )
    assert r is None


def test_approval_pending_wrong_id(_fresh_ctx):
    """已确认但 id 不匹配 → 仍 write_pending(与原逻辑一致)"""
    r = _run(
        _fresh_ctx,
        ApprovalGuard,
        {
            "tool": "write_file",
            "session_id": "s",
            "tool_call_id": "call_2",
            "args": {"path": "a.py"},
            "approved": {"id": "call_1", "approved": True},
        },
    )
    assert r is not None and r["status"] == "write_pending"


# ===== G4 PlanGuard =====


def test_plan_passes_single_file(_fresh_ctx):
    """单个写工具 → 无 plan_pending"""
    r = _run(
        _fresh_ctx,
        PlanGuard,
        {
            "tool": "write_file",
            "session_id": "s",
            "tool_calls_plan": [
                {"function": {"name": "write_file", "arguments": '{"path": "a.py"}'}},
            ],
        },
    )
    assert r is None


def test_plan_pending_multi_file(_fresh_ctx):
    """≥2 文件 → plan_pending"""
    r = _run(
        _fresh_ctx,
        PlanGuard,
        {
            "tool": "write_file",
            "session_id": "s",
            "assistant_content": "计划: 改 a.py 和 b.py",
            "tool_calls_plan": [
                {"function": {"name": "write_file", "arguments": '{"path": "a.py"}'}},
                {"function": {"name": "write_file", "arguments": '{"path": "b.py"}'}},
            ],
        },
    )
    assert r is not None and r["status"] == "plan_pending"
    assert r["plan_pending_info"]["files"] == ["a.py", "b.py"]
    assert r["plan_pending_info"]["intents"] == 2


def test_plan_pending_multi_intent(_fresh_ctx):
    """≥3 意图(单文件多次) → plan_pending"""
    r = _run(
        _fresh_ctx,
        PlanGuard,
        {
            "tool": "write_file",
            "session_id": "s",
            "assistant_content": "计划",
            "tool_calls_plan": [
                {"function": {"name": "write_file", "arguments": '{"path": "a.py"}'}},
                {"function": {"name": "write_file", "arguments": '{"path": "a.py"}'}},
                {"function": {"name": "write_file", "arguments": '{"path": "a.py"}'}},
            ],
        },
    )
    assert r is not None and r["status"] == "plan_pending"
    assert r["plan_pending_info"]["files"] == ["a.py"]
    assert r["plan_pending_info"]["intents"] == 3


def test_plan_passes_approved(_fresh_ctx):
    """已确认计划 → 放行"""
    r = _run(
        _fresh_ctx,
        PlanGuard,
        {
            "tool": "write_file",
            "session_id": "s",
            "approved": {"approved": True},
            "tool_calls_plan": [
                {"function": {"name": "write_file", "arguments": '{"path": "a.py"}'}},
                {"function": {"name": "write_file", "arguments": '{"path": "b.py"}'}},
            ],
        },
    )
    assert r is None


# ===== G7 RecursionGuard =====


def test_recursion_passes_first_call(_fresh_ctx):
    """首次调用 → 放行"""
    r = _run(
        _fresh_ctx,
        RecursionGuard,
        {
            "tool": "read_file",
            "args": {"path": "a.py"},
            "task_id": "t1",
        },
    )
    assert r is None


def test_recursion_pause_at_threshold(_fresh_ctx):
    """同一 (tool,path) 连续 5 次(auto_pause_threshold) → paused(单 guard 多 waterfall)"""
    import core.gateway.execute_agent_task as eat

    assert eat._recursion_tracker == {}, f"fixture 应清空 tracker: {eat._recursion_tracker}"
    g = RecursionGuard()
    _fresh_ctx.mount(g)
    results = []
    for i in range(5):
        results.append(
            _fresh_ctx.waterfall(
                "tools/pre-execute",
                {
                    "tool": "write_file",
                    "args": {"path": "x.py"},
                    "task_id": "t2",
                },
            )
        )
    assert results[0] is None and results[1] is None
    r = results[4]
    assert r is not None and r["status"] == "paused"
    assert "重复操作" in r["recursion_reason"] or "递归" in r["recursion_reason"]


def test_recursion_warn_at_2(_fresh_ctx):
    """第 2 次 → warn 提示(不暂停)"""
    payloads = []
    ctx = _fresh_ctx
    got = []
    ctx.on("tools/pre-execute", lambda p: got.append(p))
    g = RecursionGuard()
    ctx.mount(g)
    for i in range(2):
        pl = {"tool": "write_file", "args": {"path": "y.py"}, "task_id": "t3"}
        r = ctx.waterfall("tools/pre-execute", pl)
        payloads.append(r)
    # 第2次 warn: guard 写 guard_results 但 waterfall 返回 None
    assert payloads[0] is None and payloads[1] is None
    assert any("recursion_warn" in p.get("guard_results", {}) for p in got)
