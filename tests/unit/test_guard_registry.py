"""P1 S1: 守卫基座 + 注册表骨架测试(未接现有守卫, 零行为变化)"""
import sys, os
sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")

import pytest
from core.os.context import V9Context
from core.gateway.guards import (
    GUARD_ORDER, guard_names, mount_guards, unmount_guards, get_guard_classes,
    ToolGuard, EVENT_PRE_EXECUTE, EVENT_POST_EXECUTE,
)


@pytest.fixture(autouse=True)
def _fresh_ctx():
    return V9Context()


def test_guard_order_registry():
    """注册表 12 守卫, 顺序精确(plan 60 在 approval 70 前; web_fetch 85; 观察后置)"""
    names = guard_names()
    assert len(names) == 12
    assert names[:9] == ["quota_guard", "mode_guard", "forced_tool_guard",
                         "forbidden_guard", "escape_guard", "plan_guard",
                         "approval_guard", "recursion_guard", "web_fetch_guard"]
    assert names[9:] == ["reminder_guard", "audit_guard", "failure_pause_guard"]
    orders = [g["order"] for g in GUARD_ORDER]
    assert orders == [10, 20, 30, 40, 50, 60, 70, 80, 85, 100, 110, 120]
def test_event_split():
    """可拒绝守卫挂 pre-execute, 观察守卫挂 post-execute"""
    for g in GUARD_ORDER:
        cls = g["cls"]
        if g["name"] in ("reminder_guard", "audit_guard", "failure_pause_guard"):
            assert cls.event == EVENT_POST_EXECUTE, g["name"]
        else:
            assert cls.event == EVENT_PRE_EXECUTE, g["name"]


def test_placeholder_guards_pass_through(_fresh_ctx):
    """S1 占位守卫: check 未实现? 不 — 占位类继承 ToolGuard 但未覆写 check
    会抛 NotImplementedError, 被 _handler 捕获视为放行。挂载后 waterfall 返回 None。"""
    mounted = mount_guards(_fresh_ctx)
    assert len(mounted) == 12
    # pre-execute 守卫: 读类工具全部放行(None)
    r = _fresh_ctx.waterfall(EVENT_PRE_EXECUTE, {"tool": "read_file", "args": {}})
    assert r is None, f"守卫应全部放行读工具: {r}"
    # web_fetch_guard 对网络工具生效(同 URL 第 4 次拒绝)
    r2 = _fresh_ctx.waterfall(EVENT_PRE_EXECUTE, {"tool": "fetch_web", "args": {"url": "https://a.com/x"}, "session_id": "s1", "task_id": "t1"})
    assert r2 is None, f"首次网络抓取应放行: {r2}"
    unmount_guards(_fresh_ctx, mounted)


def test_mount_exclude_subtask_scope(_fresh_ctx):
    """子任务 scope 挂载: exclude approval/plan → 免审批语义由作用域表达"""
    mounted = mount_guards(_fresh_ctx, scope="sub_task_1",
                           exclude=["approval_guard", "plan_guard"])
    names = [g.name for g in mounted]
    assert "approval_guard" not in names
    assert "plan_guard" not in names
    assert len(names) == 10  # 12 个守卫 - approval - plan
    # scope 内 waterfall 也不触发被排除的守卫
    r = _fresh_ctx.waterfall(EVENT_PRE_EXECUTE, {}, scope="sub_task_1")
    assert r is None
    _fresh_ctx.dispose_scope("sub_task_1")


def test_mount_include_filter(_fresh_ctx):
    """include 过滤: 只挂指定守卫"""
    mounted = mount_guards(_fresh_ctx, include=["quota_guard", "escape_guard"])
    assert [g.name for g in mounted] == ["quota_guard", "escape_guard"]
    unmount_guards(_fresh_ctx, mounted)


def test_guard_deny_helper():
    """deny/observe 便捷构造"""
    d = ToolGuard.deny("配额不足", status="quota_exhausted", tool="write_file")
    assert d == {"deny": True, "reason": "配额不足", "status": "quota_exhausted", "tool": "write_file"}
    o = ToolGuard.observe(extra=1)
    assert o["deny"] is False and o["status"] == "observed" and o["extra"] == 1


def test_custom_guard_deny_shortcircuits(_fresh_ctx):
    """自定义守卫 deny → waterfall 短路, 后续守卫不执行"""
    class G1(ToolGuard):
        name = "g1"
        event = EVENT_PRE_EXECUTE
        def check(self, payload):
            return None
    class G2(ToolGuard):
        name = "g2"
        event = EVENT_PRE_EXECUTE
        def check(self, payload):
            return {"deny": True, "reason": "x", "status": "default"}
    class G3(ToolGuard):
        name = "g3"
        event = EVENT_PRE_EXECUTE
        def check(self, payload):
            raise AssertionError("不应执行")
    _fresh_ctx.mount(G1())
    _fresh_ctx.mount(G2())
    _fresh_ctx.mount(G3())
    r = _fresh_ctx.waterfall(EVENT_PRE_EXECUTE, {})
    assert r == {"deny": True, "reason": "x", "status": "default"}


def test_guard_exception_treated_as_pass(_fresh_ctx):
    """守卫 check 抛异常 → 视为放行, 不阻断"""
    class G(ToolGuard):
        name = "g"
        event = EVENT_PRE_EXECUTE
        def check(self, payload):
            raise RuntimeError("boom")
    _fresh_ctx.mount(G())
    assert _fresh_ctx.waterfall(EVENT_PRE_EXECUTE, {}) is None


def test_unmount_guards_removes_listeners(_fresh_ctx):
    """unmount 后 waterfall 不再触发守卫"""
    calls = []
    class G(ToolGuard):
        name = "g"
        event = EVENT_PRE_EXECUTE
        def check(self, payload):
            calls.append(1)
            return None
    g = G()
    _fresh_ctx.mount(g)
    _fresh_ctx.waterfall(EVENT_PRE_EXECUTE, {})
    assert calls == [1]
    _fresh_ctx.unmount(g)
    _fresh_ctx.waterfall(EVENT_PRE_EXECUTE, {})
    assert calls == [1], "卸载后不应再触发"
