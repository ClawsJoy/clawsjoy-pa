# -*- coding: utf-8 -*-
"""故障注入 · 假完成（完成核验闸门）。纪律：**先能失败，再能通过**。

背景：agent 宣称完成即可落 completed —— V7 讲义自称含 P1–P14、正文缺 P11–P13，
没有任何探测器发现。GPT 的判据：**completion 不由模型说，而是 verifier 的派生字段**。

本测试锁住 2026-09-13 接上的完成闸门：
  完成分支 → R6 产物核验 + 五步链 + 审计交叉复核 → 未过则不落 completed，
  把 failures 回灌 messages 续跑（最多 2 次防卡死）。
"""
import os
import sys

sys.path.insert(0, ".")
from core.gateway import shared_state as ss
from core.gateway.v9_bridge.response_guard import _completion_verify, _run_response_guard


def _steps_write(path, ok=True):
    return [{"tool": "write_file", "arg": path, "success": ok, "round": 1}]


def test_FAULT_placeholder_delivery_blocks_completion(tmp_path, monkeypatch):
    """① 先能失败：只写了个 68 字节占位物 → 核验必须不通过。"""
    (tmp_path / "artifact_pa_task.txt").write_text("x" * 68, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("core.lib.gateway_helpers._get_sandbox_base", lambda u, sid: str(tmp_path))
    r = _completion_verify(
        messages=[], tool_steps=_steps_write("artifact_pa_task.txt"), session_id="s_fc1", user_id="u", turn_id=1
    )
    assert r["checked"] is True
    assert r["passed"] is False
    assert any("占位" in str(x) for x in r["failures"]), r


def test_PASS_real_artifact_not_flagged_as_placeholder(tmp_path, monkeypatch):
    """② 再能通过：真产物不得被 R6 判占位。"""
    (tmp_path / "deck.md").write_text("正文" * 2000, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("core.lib.gateway_helpers._get_sandbox_base", lambda u, sid: str(tmp_path))
    r = _completion_verify(messages=[], tool_steps=_steps_write("deck.md"), session_id="s_fc2", user_id="u", turn_id=1)
    assert not any("占位" in str(x) for x in (r["failures"] or [])), r


def test_readonly_task_is_never_blocked():
    """不退化：只读任务（无写工具）必须跳过核验，不拦。"""
    steps = [
        {"tool": "read_file", "arg": "a.md", "success": True},
        {"tool": "obsidian_knowledge", "arg": "", "success": True},
    ]
    r = _completion_verify(messages=[], tool_steps=steps, session_id="s_ro", user_id="u", turn_id=1)
    assert r["checked"] is False and r["passed"] is True


def test_failed_write_does_not_trigger():
    """写失败不触发核验（本 turn 没有真写入）。"""
    r = _completion_verify(
        messages=[], tool_steps=_steps_write("x.md", ok=False), session_id="s_nw", user_id="u", turn_id=1
    )
    assert r["checked"] is False


def test_env_kill_switch(monkeypatch):
    monkeypatch.setenv("V9_COMPLETION_VERIFY", "0")
    r = _completion_verify(messages=[], tool_steps=_steps_write("x.md"), session_id="s_off", user_id="u", turn_id=1)
    assert r["checked"] is False and r["passed"] is True


def test_verifier_exception_is_swallowed(tmp_path, monkeypatch):
    """宁可不拦，不可误伤：某层核验器自己抛异常 → 该层跳过，异常文本不得变成失败原因。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("core.lib.gateway_helpers._get_sandbox_base", lambda u, sid: str(tmp_path))
    (tmp_path / "x.md").write_text("正文" * 2000, encoding="utf-8")
    import core.pa.artifact as artifact_mod

    def _boom(*a, **k):
        raise RuntimeError("核验器内部炸了")

    monkeypatch.setattr(artifact_mod, "verify_artifacts", _boom)
    msgs = [{"role": "assistant", "content": "已完成：x.md 已写入并核验。"}]
    r = _completion_verify(messages=msgs, tool_steps=_steps_write("x.md"), session_id="s_ex", user_id="u", turn_id=1)
    assert not any("核验器内部炸了" in str(x) for x in (r.get("failures") or [])), r


def test_PASS_clean_completion_goes_through(tmp_path, monkeypatch):
    """② 再能通过：真产物 + 有 agent 报告 → 核验必须放行。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("core.lib.gateway_helpers._get_sandbox_base", lambda u, sid: str(tmp_path))
    (tmp_path / "deck.md").write_text("正文" * 2000, encoding="utf-8")
    msgs = [{"role": "assistant", "content": "已完成：deck.md 已写入并核验。"}]
    r = _completion_verify(
        messages=msgs, tool_steps=_steps_write("deck.md"), session_id="s_ok3", user_id="u", turn_id=1
    )
    assert r["checked"] is True and r["passed"] is True, r


def test_retry_cap_prevents_infinite_loop():
    """最多回灌 2 次，第 3 次不再拦（防卡死）。"""
    ss.verification_retry_reset("s_cap")
    assert ss.verification_retry_bump("s_cap") is True
    assert ss.verification_retry_bump("s_cap") is True
    assert ss.verification_retry_bump("s_cap") is False
    ss.verification_retry_reset("s_cap")
    assert ss.verification_retry_bump("s_cap") is True


def _guard(**over):
    kw = dict(
        messages=[],
        data_resp={"choices": [{"message": {"content": "done"}}]},
        bmsg={"content": "已完成，结果如下。"},
        btool_calls=[],
        session_id="s_gate",
        bridge_round=1,
        turn_id=1,
        tokens=1,
        tool_steps=[],
        bridge_exhausted=False,
        empty_reply_count=0,
        no_think=False,
        detect_ask_fn=lambda m: None,
        is_plan_message_fn=lambda c: False,
        ctx_summary_fn=lambda m: "",
        write_turn_end_fn=lambda *a: None,
        ts_progress_fn=lambda: {},
        goal_info_fn=lambda sid: {},
        plan_pending={},
        user_id="u",
    )
    kw.update(over)
    return _run_response_guard(**kw)


def test_gate_only_reports_by_default(tmp_path, monkeypatch):
    """默认**只报不拦**：假交付被检出并留痕，但不打断本轮完成。

    为什么默认不拦：live 实证「续跑(verification_retry → continue)」会撞 400
    （reasoning_content must be passed back），连续两次复现且历史会话 0 次出现。
    按「不退化优先」，拦截改为 opt-in（V9_COMPLETION_VERIFY_BLOCK=1）。
    """
    (tmp_path / "artifact_pa_task.txt").write_text("x" * 68, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("core.lib.gateway_helpers._get_sandbox_base", lambda u, sid: str(tmp_path))
    monkeypatch.setattr(ss, "request_cancel", lambda sid: None)
    monkeypatch.delenv("V9_COMPLETION_VERIFY_BLOCK", raising=False)
    ss.verification_retry_reset("s_gate")
    out = _guard(session_id="s_gate", tool_steps=_steps_write("artifact_pa_task.txt"))
    assert out.get("verification_retry") is None
    assert out.get("normal_complete") is True, out


def test_gate_blocks_when_explicitly_enabled(tmp_path, monkeypatch):
    """显式打开拦截开关时，假交付必须被挡下（续跑路径本身可工作）。"""
    (tmp_path / "artifact_pa_task.txt").write_text("x" * 68, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("core.lib.gateway_helpers._get_sandbox_base", lambda u, sid: str(tmp_path))
    monkeypatch.setattr(ss, "request_cancel", lambda sid: None)
    monkeypatch.setenv("V9_COMPLETION_VERIFY_BLOCK", "1")
    ss.verification_retry_reset("s_gate")
    out = _guard(session_id="s_gate", tool_steps=_steps_write("artifact_pa_task.txt"))
    assert out.get("verification_retry") is True, out
    assert out.get("normal_complete") is False


def test_gate_passes_readonly_task(monkeypatch):
    """不退化：只读任务照常 normal_complete。"""
    monkeypatch.setattr(ss, "request_cancel", lambda sid: None)
    out = _guard(session_id="s_gate_ro", tool_steps=[{"tool": "read_file", "arg": "a.md", "success": True}])
    assert out.get("normal_complete") is True, out
