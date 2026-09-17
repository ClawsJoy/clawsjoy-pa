# -*- coding: utf-8 -*-
"""R1 守卫 + 续跑消息落盘（400 修复）回归。纪律：先能失败，再能通过。"""
import sys

sys.path.insert(0, ".")
from core.pa.decision import TASK_TEMPLATES, generate_plan


def test_FAULT_produces_must_be_sandbox_relative():
    """① 先能失败：produces 不得是裸文件名（R1）。

    背景：R6/verifier 要按会话沙箱解析产物路径；裸文件名会让判定不可靠，
    且与 R3「交付=投影」的起点对不上。
    """
    bad = []
    for tt, tmpl in TASK_TEMPLATES.items():
        for row in tmpl:
            produces = str(row[2])
            if produces.startswith("<"):
                continue  # <目标文件> 是占位语义，不参与路径约定
            if "/" not in produces:
                bad.append((tt, produces))
    assert not bad, "以下 produces 仍是裸文件名（缺沙箱相对路径）：%s" % bad


def test_PASS_all_template_produces_are_under_data_reports():
    """② 再能通过：全部落在 data/reports/ 下。"""
    for tt, tmpl in TASK_TEMPLATES.items():
        for row in tmpl:
            produces = str(row[2])
            if produces.startswith("<"):
                continue
            assert produces.startswith("data/reports/"), (tt, produces)


def test_generate_plan_steps_carry_sandbox_relative_produces():
    """端到端：计划 steps 里的 produces 也是沙箱相对路径（前端/verifier 都读它）。"""
    r = generate_plan("准备一份光电行业 PPT 讲义", mode="work")
    steps = r.get("steps") or []
    assert steps
    for s in steps:
        p = str(s.get("produces") or "")
        if p and not p.startswith("<"):
            assert p.startswith("data/reports/"), s


def test_retry_message_is_logged_as_runtime_context(monkeypatch, tmp_path):
    """400 修复：续跑注入消息必须落盘为 source=runtime_context。

    系统约定见 core/gateway/v9_bridge/loop.py:114 / core/gateway/execute_agent_task.py:979。
    不落盘 → 下一轮 derive_messages 重建时丢失 → 续跑拿同一份上下文再调 → 400。
    """
    from core.gateway import shared_state as ss
    from core.gateway.v9_bridge import response_guard as rg

    (tmp_path / "artifact_pa_task.txt").write_text("x" * 68, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("core.lib.gateway_helpers._get_sandbox_base", lambda u, s: str(tmp_path))
    monkeypatch.setattr(ss, "request_cancel", lambda sid: None)
    monkeypatch.setenv("V9_COMPLETION_VERIFY_BLOCK", "1")
    ss.verification_retry_reset("s_log")

    logged = []
    import core.gateway.session_log as slog

    monkeypatch.setattr(slog, "log_event", lambda sid, t, p=None, **kw: logged.append((t, p)))

    out = rg._run_response_guard(
        messages=[],
        data_resp={"choices": [{"message": {"content": "done"}}]},
        bmsg={"content": "已完成。"},
        btool_calls=[],
        session_id="s_log",
        bridge_round=1,
        turn_id=1,
        tokens=1,
        tool_steps=[{"tool": "write_file", "arg": "artifact_pa_task.txt", "success": True, "round": 1}],
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
    assert out.get("verification_retry") is True, out
    kinds = [t for t, _ in logged]
    assert "user_message" in kinds, logged
    payload = [p for t, p in logged if t == "user_message"][0]
    assert payload.get("source") == "runtime_context", payload
    assert "完成核验未通过" in str(payload.get("content")), payload
