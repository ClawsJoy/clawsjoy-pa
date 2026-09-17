"""断点2 强制换策略回归: 越权一次即引导 + 连续 3 次失败换工具 + 计数不破坏"""
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _iso(monkeypatch):
    import core.gateway.goal_state as gs
    import core.gateway.shared_state as ss
    import core.gateway.tool_router as tr

    _new_cf = {}
    monkeypatch.setattr(ss, "_consecutive_failures", _new_cf)
    monkeypatch.setattr(tr, "_consecutive_failures", _new_cf)
    _new_pb = {}
    monkeypatch.setattr(ss, "_paused_breakpoints", _new_pb)
    monkeypatch.setattr(tr, "_paused_breakpoints", _new_pb)
    monkeypatch.setattr(ss, "_cancel_flags", {})
    monkeypatch.setattr(gs, "_goals", {})
    yield


def test_three_failures_trigger_steer():
    """连续 3 次失败 → steer 明确'换一个工具或路径'(原 ≥5, 断点2 改 ≥3)"""
    from core.gateway.shared_state import drain_steer
    from core.gateway.tool_router import _check_consecutive_failure

    # 2 次失败 → 无 steer
    for _ in range(2):
        _check_consecutive_failure({"success": False, "error": "e"}, "read_file", "s_bp2")
    assert drain_steer("s_bp2") == [], "2 次失败不应触发 steer"
    # 第 3 次 → steer
    _check_consecutive_failure({"success": False, "error": "e"}, "read_file", "s_bp2")
    _steer = drain_steer("s_bp2")
    assert _steer and "换一个工具或路径" in _steer[0], f"3 次失败应强制换策略: {_steer}"
    # 成功重置
    _check_consecutive_failure({"success": True}, "read_file", "s_bp2")
    assert drain_steer("s_bp2") == []


def test_pause_still_at_eight():
    """计数不破坏: ≥8 仍强制暂停(断点保留)"""
    from core.gateway.shared_state import _paused_breakpoints
    from core.gateway.tool_router import _check_consecutive_failure

    r = None
    for i in range(8):
        r = _check_consecutive_failure({"success": False, "error": "e"}, "read_file", "s_pause")
    assert r.get("paused") is True, "8 次失败应暂停"
    assert _paused_breakpoints.get("s_pause", {}).get("count") == 8


def test_registry_inject_at_three():
    """P4 steer 迁移: FailurePauseGuard ≥3 不再写 inject_message(防与 tool_router steer 双份), 8 次才 paused"""
    import core.gateway.shared_state as ss
    from core.gateway.guards.registry import FailurePauseGuard

    _cf = {}
    ss._consecutive_failures = _cf
    g = FailurePauseGuard()
    payload = {"tool": "read_file", "session_id": "s_reg", "result": {"success": False, "error": "e"}}
    for _ in range(3):
        g.check(payload)
    assert "inject_message" not in payload.get("guard_results", {}), "P4 后 ≥3 不写 inject_message(steer 通道承担)"
    for _ in range(5):
        g.check(payload)
    assert payload["guard_results"]["paused"], "8 次失败应 paused"


def test_escalation_immediate_guidance_source():
    """越权一次即引导: escalation 终止块注入路径引导 + add_steer(不等 5 次失败)"""
    src = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    _idx = src.index('if _term_kind == "escalation_blocked":')
    _seg = src[_idx : _idx + 900]
    assert "该路径被拦截，请换沙箱内或项目根路径" in _seg, "越权应立即引导换路径"
    assert "add_steer(session_id" in _seg and "越权路径被拦截" in _seg, "越权应走 steer 通道"
    assert "不要重复尝试被拒路径" in _seg


def test_escape_guard_catches_read_escapes():
    """断点2: 读工具越权一次即拦(只读白名单: 沙箱/会话目录/项目根外如 /etc/passwd)"""
    from core.gateway.guards.registry import EscapeGuard

    g = EscapeGuard()
    _sb = "data/projects/u1/s1/clawsjoy_dev"
    d = g.check({"tool": "read_file", "args": {"path": "/etc/passwd"}, "session_id": "s", "sandbox_base": _sb})
    assert d is not None and d.get("status") == "escalation_blocked", "系统绝对路径应拦截"
    d2 = g.check({"tool": "list_dir", "args": {"path": "/home"}, "session_id": "s", "sandbox_base": _sb})
    assert d2 is not None and d2.get("status") == "escalation_blocked", "list_dir 系统路径应拦截"
    # 只读白名单放行: 项目相对路径
    d3 = g.check(
        {"tool": "read_file", "args": {"path": "core/gateway/session_log.py"}, "session_id": "s", "sandbox_base": _sb}
    )
    assert d3 is None, "项目相对路径应放行(回退项目根)"
    # 写工具越权仍拦(回归)
    d4 = g.check({"tool": "write_file", "args": {"path": "/etc/x"}, "session_id": "s", "sandbox_base": _sb})
    assert d4 is not None and d4.get("status") == "escalation_blocked"


def test_plugin_read_fallback_project_root():
    """桥接路径插件: read_file 沙箱无 → 回退项目根 + source=project_root"""
    import types
    from pathlib import Path

    from core.gateway.path_utils import _resolve_path
    from core.tools.read_file import ReadFilePlugin

    base = Path("data/projects/u_zz/s_zz/clawsjoy_dev")
    ctx = types.SimpleNamespace(
        messages=[],
        consecutive_reads={},
        user_id="u_zz",
        session_id="s_zz",
        base=base,
        classify_task_type=lambda m: "analysis",
        get_skeleton_by_path=lambda *a: None,
        is_repeat_read_attempt=lambda *a: False,
        is_stale_read=lambda *a: False,
        resolve_path=lambda b, p: _resolve_path(b, p),
        tool_executor=types.SimpleNamespace(execute=lambda *a, **k: {"success": True, "content": "X", "cached": False}),
    )
    r = ReadFilePlugin().execute({"path": "core/gateway/session_log.py", "lines_start": 1, "lines_end": 1}, ctx)
    assert r.get("success") and r.get("source") == "project_root", r


def test_frontend_escalation_continues():
    """前端: 越权后注入拉回消息并 continue(原 return 停住, LLM 无法换路径)"""
    src = open("web/static/js/chat.js", encoding="utf-8").read()
    _idx = src.index("if (d.status === 'escalation_blocked') {")
    _seg = src[_idx : _idx + 1500]
    assert "messages.push({ role: 'assistant', content: escMsg })" in _seg
    assert "continue;" in _seg, "越权后应继续循环让 LLM 换路径"
