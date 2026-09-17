"""#12 工具优先级抢占回归测试: 优先级表 + 抢占请求队列 + 工具执行入口打断"""
import json
import sys

sys.path.insert(0, ".")
import pytest


def test_tool_priority_table():
    """工具优先级: 读类1 < 写类2 < 浏览器3; 未注册默认1"""
    from core.gateway.tool_router import _TOOL_PRIORITY, _tool_priority

    assert _tool_priority("read_file") == 1
    assert _tool_priority("list_dir") == 1
    assert _tool_priority("write_file") == 2
    assert _tool_priority("execute_command") == 2
    assert _tool_priority("browser_local") == 3
    assert _tool_priority("playwright_browser") == 3
    assert _tool_priority("unknown_tool") == 1
    assert _tool_priority("") == 1
    assert "read_file" in _TOOL_PRIORITY and "execute_command" in _TOOL_PRIORITY


def test_preempt_request_and_peek():
    """登记抢占请求 → peek 可见最高优先级"""
    from core.gateway.shared_state import clear_preempt, peek_preempt, request_preempt

    clear_preempt("sess_preempt_1")
    request_preempt("sess_preempt_1", priority=5, reason="紧急")
    request_preempt("sess_preempt_1", priority=3, reason="一般")
    top = peek_preempt("sess_preempt_1")
    assert top and top["priority"] == 5, f"应按优先级降序: {top}"
    assert top["reason"] == "紧急" and top["requester"] == "boss"
    clear_preempt("sess_preempt_1")
    assert peek_preempt("sess_preempt_1") is None


def test_drain_preempt_lower_priority_not_preempted():
    """请求优先级 <= 当前工具优先级 → 不打断, 且请求保留"""
    from core.gateway.shared_state import clear_preempt, drain_preempt, request_preempt

    clear_preempt("sess_preempt_2")
    request_preempt("sess_preempt_2", priority=1, reason="低优请求")
    # 当前工具优先级 2(写类) ≥ 请求 1 → 不打断
    got = drain_preempt("sess_preempt_2", current_priority=2, current_tool="write_file")
    assert got is None, "低优请求不应打断高优工具"
    assert drain_preempt("sess_preempt_2", current_priority=2, current_tool="write_file") is None
    clear_preempt("sess_preempt_2")


def test_drain_preempt_higher_priority_preempts():
    """请求优先级 > 当前工具优先级 → 打断, 返回请求且消费"""
    from core.gateway.shared_state import clear_preempt, drain_preempt, peek_preempt, request_preempt

    clear_preempt("sess_preempt_3")
    request_preempt("sess_preempt_3", priority=9, reason="老板紧急指令")
    got = drain_preempt("sess_preempt_3", current_priority=1, current_tool="read_file")
    assert got is not None, "高优请求应打断低优工具"
    assert got["priority"] == 9 and "老板" in got["reason"]
    # 消费后队列空
    assert peek_preempt("sess_preempt_3") is None
    clear_preempt("sess_preempt_3")


def test_drain_preempt_target_tool_filter():
    """target_tool 指定: 只打断指定工具, 其他工具不打断"""
    from core.gateway.shared_state import clear_preempt, drain_preempt, request_preempt

    clear_preempt("sess_preempt_4")
    request_preempt("sess_preempt_4", priority=9, reason="只打断命令", target_tool="execute_command")
    # 当前是 read_file(非目标) → 不打断
    got = drain_preempt("sess_preempt_4", current_priority=1, current_tool="read_file")
    assert got is None, "target_tool 不匹配不应打断"
    # 当前是 execute_command(目标) → 打断
    got2 = drain_preempt("sess_preempt_4", current_priority=1, current_tool="execute_command")
    assert got2 is not None and got2["target_tool"] == "execute_command"
    clear_preempt("sess_preempt_4")


def test_preempt_via_execute_sandbox_tool(monkeypatch):
    """工具执行入口: 高优请求存在 → 返回 preempted 结果"""
    import core.gateway.tool_router as tr
    from core.gateway.shared_state import clear_preempt, request_preempt

    # 用 __wrapped__ 取裸函数(跳过 SAG/audit 落库), 不 reload 模块(避免污染 v9_context 容器)
    _raw = tr._execute_sandbox_tool.__wrapped__
    monkeypatch.setattr(tr, "_get_sandbox_base", lambda u, s: type("B", (), {"exists": lambda self: True})())
    clear_preempt("sess_preempt_5")
    request_preempt("sess_preempt_5", priority=9, reason="抢占测试")
    res = _raw("read_file", {"path": "/tmp/x.txt"}, "u1", "sess_preempt_5")
    assert res.get("preempted") is True, f"应返回 preempted: {res}"
    assert res.get("preempted_by_priority") == 9
    assert res.get("success") is False
    clear_preempt("sess_preempt_5")


def test_preempt_route_registered():
    """网关含 /v9/preempt 路由 + shared_state 接口"""
    _SRC = open("routes/session.py", encoding="utf-8").read()
    assert '"/v9/preempt"' in _SRC, "缺 /v9/preempt 路由"
    assert "request_preempt(" in _SRC, "路由应调用 request_preempt"
    from core.gateway.shared_state import clear_preempt, drain_preempt, peek_preempt, request_preempt

    assert callable(request_preempt) and callable(drain_preempt)


def test_preempt_starve_guard():
    """#12审核修复: 同工具连续被抢占达上限 → 放行(防饿死)"""
    from core.gateway.shared_state import _PREEMPT_MAX_STARVE, clear_preempt, drain_preempt, request_preempt

    clear_preempt("sess_starve")
    # 连续 3 次高优抢占同一低优工具(read_file): 前 3 次打断, 第 4 次放行
    for i in range(_PREEMPT_MAX_STARVE + 1):
        request_preempt("sess_starve", priority=9, reason=f"紧急{i}")
        got = drain_preempt("sess_starve", current_priority=1, current_tool="read_file")
        if i < _PREEMPT_MAX_STARVE:
            assert got is not None, f"第{i+1}次应打断"
        else:
            assert got is None, f"第{i+1}次应放行(防饿死)"
    clear_preempt("sess_starve")


def test_preempt_starve_reset_after_pass():
    """#12审核修复: 放行后计数重置, 新抢占重新计数"""
    from core.gateway.shared_state import _PREEMPT_MAX_STARVE, clear_preempt, drain_preempt, request_preempt

    clear_preempt("sess_starve2")
    for i in range(_PREEMPT_MAX_STARVE + 1):
        request_preempt("sess_starve2", priority=9, reason=f"e{i}")
        drain_preempt("sess_starve2", current_priority=1, current_tool="read_file")
    # 放行后: 新请求应再次打断(计数已重置)
    request_preempt("sess_starve2", priority=9, reason="new")
    got = drain_preempt("sess_starve2", current_priority=1, current_tool="read_file")
    assert got is not None, "放行后新抢占应重新生效"
    clear_preempt("sess_starve2")
