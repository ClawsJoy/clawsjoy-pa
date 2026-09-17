"""#1 协作取消回归测试: 取消标志语义 + bridge/exec 检查点 + 路由 + 前端"""
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    import core.gateway.shared_state as ss

    monkeypatch.setattr(ss, "_cancel_flags", {})
    yield


def test_cancel_flag_roundtrip():
    """取消标志: request → is_set True; reset → False; 幂等"""
    from core.gateway.shared_state import is_cancel_requested, request_cancel, reset_cancel

    assert is_cancel_requested("s_c1") is False
    request_cancel("s_c1")
    assert is_cancel_requested("s_c1") is True
    request_cancel("s_c1")  # 幂等
    assert is_cancel_requested("s_c1") is True
    reset_cancel("s_c1")
    assert is_cancel_requested("s_c1") is False
    # 空 session 安全
    assert is_cancel_requested("") is False


def test_cancel_isolated_per_session():
    """取消按 session 隔离: 一个 session 取消不影响其他"""
    from core.gateway.shared_state import is_cancel_requested, request_cancel

    request_cancel("s_a")
    assert is_cancel_requested("s_a") is True
    assert is_cancel_requested("s_b") is False


def test_bridge_checkpoints_source():
    """bridge_loop 4 检查点源码: 任务开始 reset + 每轮前/池前/轮后 is_cancel_requested"""
    src = (
        open("agent_gateway_enhanced.py", encoding="utf-8").read()
        + open("core/gateway/v9_chat/recovery.py", encoding="utf-8").read()
    )  # P3-B: G 块已归位
    assert "reset_cancel(session_id)" in src, "任务开始应清旧取消标记"
    assert src.count("is_cancel_requested(session_id)") >= 2, "应有轮前/轮后检查点(D2 池前已归位 tool_runner)"
    assert "_cancelled = False" in src, "应有取消标记初始化"
    # 检查点位置: 轮前检查在 LLM 调用(call_bridge_llm)之前
    _i_pre = src.index("if is_cancel_requested(session_id):")
    _i_exec = src.index("call_bridge_llm(")
    assert _i_pre < _i_exec, "轮前检查应在 LLM 调用前"
    # 池前检查已归位 tool_runner._run_exec_phase
    _TR = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "is_cancel_requested(session_id)" in _TR, "池前检查应归位 tool_runner"
    assert "ThreadPoolExecutor" in _TR, "并行池应归位 tool_runner"
    # reason=cancelled
    _TP = open("core/gateway/turn_protocol.py", encoding="utf-8").read()  # P3-A: _write_turn_end 已归位
    assert '"cancelled"' in _TP, "应有 cancelled reason"


def test_bridge_cancel_skips_fake_done():
    """取消后跳过防虚假完成(data_resp 可能为 None 不崩)"""
    src = open("core/gateway/completion_guard.py", encoding="utf-8").read()
    assert "if cancelled or not data_resp:" in src, "取消时应跳过防假完成"


def test_cancel_route_registered():
    """POST /v9/cancel 路由 + request_cancel"""
    src = open("routes/session.py", encoding="utf-8").read()
    assert '"/v9/cancel/<path:session_id>"' in src
    assert "from core.gateway.shared_state import request_cancel" in src
    assert '"cancelled": True' in src


def test_exec_path_cancel():
    """exec 路径同构: 每轮检查 + cancelled turn_end"""
    src = open("core/gateway/execute_agent_task.py", encoding="utf-8").read()
    assert "is_cancel_requested(_sid)" in src, "exec 路径应检查取消"
    assert '"cancelled"' in src, "exec 路径应有 cancelled reason"


def test_frontend_cancel_wiring():
    """前端: 停止按钮 + AbortController + POST /v9/cancel + cancelled 分支"""
    # 模块化拆分后: 停止按钮 HTML 在 workbench.html, 取消逻辑在 chat.js
    html = open("web/dashboard/workbench.html", encoding="utf-8").read()
    src = open("web/static/js/chat.js", encoding="utf-8").read()
    assert 'id="agentStopBtn"' in html, "应有停止按钮"
    assert "AbortController" in src, "应挂 AbortController"
    # 跨线程隔离修复: 取消请求用运行时 _curSession()(非模块快照)
    assert "'/v9/cancel/' + encodeURIComponent(_curSession())" in src, "停止应通知服务端(当前线程)"
    assert "turnReason === 'cancelled'" in src and "turnReason2 === 'cancelled'" in src, "两个循环都应有 cancelled 分支"


class _StubAdapter:
    """不应被调用的 stub: 取消路径在 LLM 调用前退出"""

    def __init__(self):
        self.called = False

    def execute_with_tools(self, **kw):
        self.called = True
        return {"success": True, "data": {"choices": [{"message": {"content": "不应到达"}}]}, "tokens": 1}


def test_bridge_round_start_cancel_behavior(monkeypatch, tmp_path):
    """行为级: 取消标志置位后启动 bridge_loop → 首轮检查点退出, reason=cancelled, 不调 LLM"""
    import agent_gateway_enhanced as main
    import core.gateway.session_log as sl
    import core.gateway.shared_state as ss

    monkeypatch.setattr(sl, "_logs", {})
    _orig = sl.get_session_log

    def _get_iso(sid, base_dir=None):
        return _orig(sid, base_dir=tmp_path)

    monkeypatch.setattr(sl, "get_session_log", _get_iso)
    monkeypatch.setattr(ss, "_cancel_flags", {})
    from core.gateway.shared_state import request_cancel

    request_cancel("s_br1")
    adapter = _StubAdapter()
    out = main._v9_bridge_loop(
        messages=[{"role": "user", "content": "任务"}],
        tools=[],
        user_id="u1",
        session_id="s_br1",
        adapter=adapter,
        _thinking2=False,
        model="x",
    )
    # 7-tuple: (messages, tool_steps, bridge_exhausted, final_resp, tokens, reason, reason_detail)
    assert out[5] == "cancelled", f"reason 应为 cancelled: {out[5]}"
    assert "取消" in out[6]
    assert out[2] is True, "bridge_exhausted 应为 True"
    assert adapter.called is False, "取消后不应调用 LLM"
    # turn_end 事件带 cancelled
    evs = [ev.payload for ev in sl.get_session_log("s_br1")._events if ev.type == "turn_end"]
    assert evs and evs[0].get("reason") == "cancelled", evs
