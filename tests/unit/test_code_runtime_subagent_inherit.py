"""#3 Code Runtime stdout 截断 + #4 子代理 goal 继承回归测试"""
import sys
sys.path.insert(0, ".")
import pytest


# ================= #3 stdout/stderr 截断 =================

def test_truncate_cmd_output():
    """短输出原样; 超限保留头尾 + [TRUNCATED] 标记"""
    from core.tools.execute_command import _truncate_cmd_output
    assert _truncate_cmd_output("short", 100) == "short"
    body = "HEAD" + "m" * 9990 + "TAIL"
    out = _truncate_cmd_output(body, 8000)
    assert len(out) <= 8000 + 200, f"截断后应≤限长+标记: {len(out)}"
    assert out.startswith("HEAD") and out.endswith("TAIL")
    assert "[TRUNCATED]" in out and "超限 8000" in out


def test_execute_command_huge_output_truncated():
    """行为级: 命令输出 >8KB → stdout 截断带标记; stderr 同样"""
    from core.tools.execute_command import ExecuteCommandPlugin, _CMD_STDOUT_LIMIT
    import types
    from pathlib import Path
    import tempfile
    base = Path(tempfile.mkdtemp())
    ctx = types.SimpleNamespace(
        base=base, user_id="u1", session_id="s1", messages=[],
        normalize_path=lambda *a: base, check_sandbox_read=lambda c: None,
        sandbox_env=dict(os_environ_placeholder=""),
    )
    # Windows(2026-09-17): 本机没有 python3 这个名字, 用当前解释器(sys.executable)
    _py = sys.executable or "python3"
    # Windows(2026-09-17): 本机没有 python3 这个名字(且 Win 下 -c 引号嵌套易碎),
    # 改成"当前解释器 + 临时脚本文件"的跨平台写法, 断言意图不变。
    _py = sys.executable or "python3"
    _emit = base / "emit_huge.py"
    _emit.write_text("print('x' * 20000)\n", encoding="utf-8")
    r = ExecuteCommandPlugin().execute({"command": '"%s" "%s"' % (_py, _emit)}, ctx)
    assert r.get("success") is True
    out = r.get("stdout", "")
    assert len(out) <= _CMD_STDOUT_LIMIT + 200, f"stdout 应截断: {len(out)}"
    assert "[TRUNCATED]" in out, "超限 stdout 应有标记"


def test_execute_command_short_output_untouched():
    """小输出原样(不误截)"""
    from core.tools.execute_command import ExecuteCommandPlugin
    import types
    from pathlib import Path
    import tempfile
    base = Path(tempfile.mkdtemp())
    ctx = types.SimpleNamespace(
        base=base, user_id="u1", session_id="s1", messages=[],
        normalize_path=lambda *a: base, check_sandbox_read=lambda c: None,
        sandbox_env=dict(os_environ_placeholder=""),
    )
    r = ExecuteCommandPlugin().execute({"command": "echo ok"}, ctx)
    assert r.get("success") is True
    assert "ok" in r.get("stdout", "")


def test_heredoc_branch_truncated_source():
    """heredoc 分支同样截断(源码级)"""
    src = open("core/tools/execute_command.py", encoding="utf-8").read()
    assert "_CMD_STDOUT_LIMIT = 8000" in src
    assert src.count("_truncate_cmd_output") >= 4, "普通+heredoc 分支都应截断"
    assert "_res_h.stdout, _CMD_STDOUT_LIMIT" in src, "heredoc stdout 应截断"


# ================= #4 子代理 goal 继承 =================

@pytest.fixture(autouse=True)
def _iso(monkeypatch, tmp_path):
    """goal_state + session_log 隔离"""
    import core.gateway.goal_state as gs
    import core.gateway.session_log as sl
    import core.gateway.shared_state as ss
    monkeypatch.setattr(gs, "_goals", {})
    monkeypatch.setattr(gs, "_GOALS_ROOT", tmp_path)
    monkeypatch.setattr(sl, "_logs", {})
    _orig = sl.get_session_log
    def _get_iso(sid, base_dir=None):
        return _orig(sid, base_dir=tmp_path)
    monkeypatch.setattr(sl, "get_session_log", _get_iso)
    monkeypatch.setattr(ss, "_consecutive_failures", {})
    monkeypatch.setattr(ss, "_cancel_flags", {})
    yield


def test_subtask_inherits_parent_goal_source():
    """源码级: subtask_executor 注入 200 字继承摘要 + 传 parent_goal_id; 不传完整 messages"""
    src = open("core/gateway/subtask_executor.py", encoding="utf-8").read()
    assert "get_goal_by_session_id(session_id)" in src, "应查父 goal"
    assert "_inherit_ctx" in src and "[:200]" in src, "继承上下文应限 200 字"
    assert "parent_goal_id=_parent_goal_id" in src, "应传 parent_goal_id"
    assert "_sub_messages" in src, "应构建子任务消息(不直接透传父 messages)"


def test_exec_fallback_parent_goal_source():
    """源码级: _write_exec_turn_end 子会话查无 → get_goal_by_id(parent_goal_id) 回退"""
    src = open("core/gateway/execute_agent_task.py", encoding="utf-8").read()
    assert "parent_goal_id=None" in src, "应有 parent_goal_id 参数"
    assert "get_goal_by_id(parent_goal_id)" in src, "应回退查父 goal"
    assert '_g_sid = _g_e.get("session_id") or _sid' in src, "应使用父 goal 自身 session"


def test_parent_goal_progress_advances(tmp_path):
    """行为级: 父 goal 存在 → create_goal; get_goal_by_id 跨会话命中(回退基础)"""
    from core.gateway.goal_state import create_goal, update_goal_progress, get_goal_by_id
    g = create_goal("u9", "parent_sess", "父任务: 重构模块", plan=["a", "b"])
    # 模拟子会话回退: get_goal_by_id(父 goal_id) 命中
    assert get_goal_by_id(g["goal_id"])["objective"] == "父任务: 重构模块"
    # 进度推进按父 goal 自身 user/session
    g2 = update_goal_progress("u9", "parent_sess", done=1, total=2, turn_id=99)
    assert g2["progress"]["done"] == 1 and g2["source_turn"] == 99
