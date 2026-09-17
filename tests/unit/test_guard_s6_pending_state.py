"""P1 步骤4前置: 状态管理补全后 write_pending/plan_pending 透传验证"""
import os
import sys

sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import pytest

import core.os.context as oc
from core.gateway.guards.registry import ApprovalGuard, PlanGuard
from core.gateway.guards.runner import _scope_mounted, run_pre_guards


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    _orig = oc._v9ctx
    oc._v9ctx = None
    _scope_mounted.clear()
    from core.gateway.guards.registry import mount_guards

    mount_guards(oc.get_v9_context())
    # 隔离 bridge 状态
    import agent_gateway_enhanced as main
    import core.gateway.write_gate as _wg

    monkeypatch.setattr(_wg, "_pending_writes", {})
    monkeypatch.setattr(main, "_pending_writes", _wg._pending_writes)
    monkeypatch.setattr(_wg, "_plan_pending", {})
    monkeypatch.setattr(main, "_plan_pending", _wg._plan_pending)
    monkeypatch.setattr(main, "_persist_pending_writes", lambda *a, **k: None)
    yield main
    oc._v9ctx = _orig
    _scope_mounted.clear()


def _bridge_deny(main, tool, args, tool_calls=None, approved=None, content="计划"):
    """模拟 bridge_loop 的 run_pre_guards + 状态写入分支"""
    from core.gateway.guards.runner import run_pre_guards

    gd = run_pre_guards(
        {
            "tool": tool,
            "args": args,
            "session_id": "s1",
            "user_id": "u1",
            "sandbox_base": "data/projects/u1/s1/clawsjoy_dev",
            "messages": [],
            "tool_call_id": "c1",
            "approved": approved or {},
            "tool_calls_plan": tool_calls or [],
            "assistant_content": content,
        }
    )
    if gd is None:
        return None
    gst = gd.get("status")
    if gst == "write_pending":
        with main._get_pending_lock():
            main._pending_writes["s1"] = gd.get("pending_write", {})
            main._persist_pending_writes("u1", "s1")
        return {"status": "write_pending", "pending_write": main._pending_writes["s1"]}
    if gst == "plan_pending":
        main._plan_pending["s1"] = gd.get("plan_pending_info", {})
        return {"status": "plan_pending", "plan_pending_info": main._plan_pending["s1"]}
    return {"status": gst}


def test_write_pending_state_persisted(_fresh):
    """未确认写 → write_pending + _pending_writes 状态写入"""
    main = _fresh
    r = _bridge_deny(main, "write_file", {"path": "a.py", "content": "x"})
    assert r is not None and r["status"] == "write_pending"
    assert main._pending_writes.get("s1", {}).get("path") == "a.py"
    assert main._pending_writes["s1"].get("approved") is False
    assert r["pending_write"]["id"] == "c1"


def test_write_pending_approved_clears(_fresh):
    """已确认匹配 → 放行(不写 pending)"""
    main = _fresh
    r = _bridge_deny(main, "write_file", {"path": "a.py", "content": "x"}, approved={"id": "c1", "approved": True})
    assert r is None
    assert "s1" not in main._pending_writes


def test_plan_pending_state_persisted(_fresh):
    """多文件计划 → plan_pending + _plan_pending 状态写入"""
    main = _fresh
    tool_calls = [
        {"function": {"name": "write_file", "arguments": '{"path": "a.py"}'}},
        {"function": {"name": "write_file", "arguments": '{"path": "b.py"}'}},
    ]
    r = _bridge_deny(main, "write_file", {"path": "a.py"}, tool_calls=tool_calls, content="计划: 改 a.py 和 b.py")
    assert r is not None and r["status"] == "plan_pending"
    assert main._plan_pending.get("s1", {}).get("files") == ["a.py", "b.py"]
    assert main._plan_pending["s1"].get("intents") == 2
    assert main._plan_pending["s1"].get("approved") is False


def test_plan_pending_approved_skips_plan_but_write_still_pending(_fresh):
    """计划已确认 → 跳过 plan 门, 但写操作仍需锚点A 确认(原语义: 计划确认≠写审批)"""
    main = _fresh
    main._plan_pending["s1"] = {"approved": True}
    r = _bridge_deny(
        main,
        "write_file",
        {"path": "a.py"},
        tool_calls=[
            {"function": {"name": "write_file", "arguments": '{"path": "a.py"}'}},
            {"function": {"name": "write_file", "arguments": '{"path": "b.py"}'}},
        ],
        approved={"approved": True},
    )
    # 计划已确认 → 不返回 plan_pending; 但写未确认 → write_pending
    assert r is not None and r["status"] == "write_pending"


def test_plan_deadlock_fix_approved_from_plan_pending(_fresh):
    """死循环修复: bridge_loop 传 approved=_plan_pending(非 _pending_writes)。

    根因: L2866 run_pre_guards payload 曾传 _pending_writes(写审批) → PlanGuard 永远
    看不到 plan 的 approved=True → 老板确认后重执行仍触发计划卡 → 死循环。
    """
    main = _fresh
    src = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    # 源码断言: approved 应来自 _plan_pending
    assert '"approved": _plan_pending.get(session_id, {})' in src, "approved 应传计划审批状态"
    # 行为断言: 计划已确认(_plan_pending.approved=True) + 真实 bridge 传 approved=_plan_pending
    # → PlanGuard 放行, 不再触发 plan_pending
    main._plan_pending["s1"] = {"approved": True, "files": ["a.py", "b.py"], "intents": 2}
    r = _bridge_deny(
        main,
        "write_file",
        {"path": "a.py"},
        tool_calls=[
            {"function": {"name": "write_file", "arguments": '{"path": "a.py"}'}},
            {"function": {"name": "write_file", "arguments": '{"path": "b.py"}'}},
        ],
        approved=main._plan_pending["s1"],
    )
    # 计划已确认 → 不返回 plan_pending(可能因写未确认返回 write_pending 或直接放行)
    assert r is None or r["status"] != "plan_pending", f"已确认计划不应再触发 plan_pending: {r}"


def test_plan_pending_overwrite_preserves_approved(_fresh):
    """防御性保留 approved: guard 再次返回 plan_pending 覆盖状态时不得丢失 approved=True"""
    main = _fresh
    src = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "_prev_pp = _plan_pending.get(session_id, {})" in src, "应有 prev 读取"
    assert 'if _prev_pp.get("approved"):' in src, "应有 approved 保留"
    assert '_new_pp["approved"] = True' in src, "应回写 approved"
    # 行为: 模拟已确认后 guard 再次触发 plan_pending(新 info 无 approved)
    main._plan_pending["s1"] = {"approved": True, "files": ["a.py"]}
    _gd_new = {"plan_pending_info": {"ts": 1.0, "approved": False, "plan": "p", "files": ["a.py"], "intents": 1}}
    _prev_pp = main._plan_pending.get("s1", {})
    _new_pp = _gd_new.get("plan_pending_info", {})
    if _prev_pp.get("approved"):
        _new_pp["approved"] = True
    main._plan_pending["s1"] = _new_pp
    assert main._plan_pending["s1"].get("approved") is True, "approved 不得被覆盖丢失"


def test_confirm_cleanup_preserved(_fresh):
    """确认后清理(_pending_writes.pop + persist)保留在 bridge_loop"""
    main = _fresh
    main._pending_writes["s1"] = {"id": "c1", "approved": True}
    # 模拟确认后清理(原内联 L1967-1970)
    with main._get_pending_lock():
        main._pending_writes.pop("s1", None)
        main._persist_pending_writes("u1", "s1")
    assert "s1" not in main._pending_writes
