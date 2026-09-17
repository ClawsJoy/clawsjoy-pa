"""P1 S6: 守卫执行器统一入口测试 — runner + 子任务免审批 scope"""
import sys, os
sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")

import pytest
import core.os.context as oc


@pytest.fixture(autouse=True)
def _fresh_global_ctx(monkeypatch):
    """独立全局单例(不污染进程级)"""
    orig = oc._v9ctx
    oc._v9ctx = None
    from core.gateway.guards.runner import _scope_mounted
    _scope_mounted.clear()
    yield oc.get_v9_context()
    oc._v9ctx = orig
    _scope_mounted.clear()


def test_run_pre_guards_passes(_fresh_global_ctx):
    """全量守卫挂载后, 正常工具放行"""
    from core.gateway.guards.registry import mount_guards
    mount_guards(_fresh_global_ctx)
    from core.gateway.guards.runner import run_pre_guards
    r = run_pre_guards({
        "tool": "read_file", "args": {"path": "a.py"},
        "session_id": "s1", "user_id": "u1",
        "sandbox_base": "/tmp/sbx", "messages": [],
    })
    assert r is None, f"正常工具应放行: {r}"


def test_run_pre_guards_forbidden(_fresh_global_ctx):
    """禁则拒绝: write_file 写共享配置"""
    from core.gateway.guards.registry import mount_guards
    mount_guards(_fresh_global_ctx)
    from core.gateway.guards.runner import run_pre_guards
    r = run_pre_guards({
        "tool": "write_file", "args": {"path": "core/lib/filter_net.json"},
        "session_id": "s2", "user_id": "u1",
        "sandbox_base": "/tmp/sbx", "messages": [],
    })
    assert r is not None and r["status"] == "forbidden"


def test_run_pre_guards_escape(_fresh_global_ctx):
    """越权拒绝: 写沙箱外绝对路径"""
    from core.gateway.guards.registry import mount_guards
    mount_guards(_fresh_global_ctx)
    from core.gateway.guards.runner import run_pre_guards
    r = run_pre_guards({
        "tool": "write_file", "args": {"path": "/etc/passwd"},
        "session_id": "s3", "user_id": "u1",
        "sandbox_base": "/tmp/sbx", "messages": [],
    })
    assert r is not None and r["status"] == "escalation_blocked"


def test_run_pre_guards_write_pending(_fresh_global_ctx):
    """未确认写 → write_pending"""
    from core.gateway.guards.registry import mount_guards
    mount_guards(_fresh_global_ctx)
    from core.gateway.guards.runner import run_pre_guards
    r = run_pre_guards({
        "tool": "write_file", "args": {"path": "a.py", "content": "x"},
        "session_id": "s4", "user_id": "u1", "tool_call_id": "c1",
        "sandbox_base": "/tmp/sbx", "messages": [],
        "approved": {},
    })
    assert r is not None and r["status"] == "write_pending"
    assert r["pending_write"]["path"] == "a.py"


def test_run_pre_guards_subtask_scope_no_approval(_fresh_global_ctx):
    """子任务 scope: 免审批 — 未确认写也放行(不挂 approval/plan/escape)"""
    from core.gateway.guards.runner import run_pre_guards
    r = run_pre_guards({
        "tool": "write_file", "args": {"path": "a.py", "content": "x"},
        "session_id": "s5", "user_id": "u1", "tool_call_id": "c1",
        "sandbox_base": "/tmp/sbx", "messages": [],
        "approved": {},
    }, scope_key="s5_sub_1")
    # 子任务 scope 免审批: approval 未挂 → 放行(除非其他 guard 拒绝)
    assert r is None, f"子任务写应免审批放行: {r}"


def test_run_post_guards_writes_guard_results(_fresh_global_ctx, monkeypatch):
    """post 观察守卫写 guard_results"""
    from core.gateway.guards.registry import mount_guards
    mount_guards(_fresh_global_ctx)
    from core.gateway.guards.runner import run_post_guards
    from core.gateway import repeat_tool_reminder as rtr
    rtr._counts.clear()
    payload = {
        "tool": "read_file", "args": {"path": "a.py"},
        "session_id": "s6", "user_id": "u1",
        "result": {"success": True}, "agent_id": "s6",
    }
    run_post_guards(payload)
    assert "guard_results" in payload


def test_run_post_guards_subtask_scope(_fresh_global_ctx, monkeypatch):
    """子任务 scope post 观察: 重复提醒计数"""
    from core.gateway.guards.runner import run_post_guards
    from core.gateway import repeat_tool_reminder as rtr
    rtr._counts.clear()
    from core.gateway.guards.registry import mount_guards
    mount_guards(_fresh_global_ctx, scope="s7_sub", exclude=["approval_guard", "plan_guard", "escape_guard"])
    # 连续 3 次同工具同参数
    for i in range(3):
        payload = {
            "tool": "read_file", "args": {"path": "a.py"},
            "session_id": "s7", "user_id": "u1",
            "result": {"success": True}, "agent_id": "s7",
        }
        run_post_guards(payload, scope_key="s7_sub")
        if i == 2:
            assert "reminder" in payload.get("guard_results", {}), f"第3次应有提醒: {payload.get('guard_results')}"
