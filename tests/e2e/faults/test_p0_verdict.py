# -*- coding: utf-8 -*-
"""P0-1 verdict 驱动完成的回归。完成与否由 verifier 的 verdict 派生。"""
import sys

sys.path.insert(0, ".")
from core.gateway.v9_bridge.response_guard import _completion_verify


def _steps(path):
    return [{"tool": "write_file", "arg": path, "success": True, "round": 1}]


def test_FAULT_stub_is_not_pass(tmp_path, monkeypatch):
    (tmp_path / "artifact_pa_task.txt").write_text("x" * 68, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("core.lib.gateway_helpers._get_sandbox_base", lambda u, s: str(tmp_path))
    r = _completion_verify(
        messages=[], tool_steps=_steps("artifact_pa_task.txt"), session_id="v1", user_id="u", turn_id=1
    )
    assert r["verdict"] == "FAIL", r


def test_PASS_real_delivery_is_pass(tmp_path, monkeypatch):
    (tmp_path / "deck.md").write_text("正文" * 2000, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("core.lib.gateway_helpers._get_sandbox_base", lambda u, s: str(tmp_path))
    msgs = [{"role": "assistant", "content": "已完成：deck.md 已写入并核验。"}]
    r = _completion_verify(messages=msgs, tool_steps=_steps("deck.md"), session_id="v2", user_id="u", turn_id=1)
    assert r["verdict"] == "PASS", r


def test_readonly_task_is_not_applicable():
    """纯问答/只读任务 → NOT_APPLICABLE（不是 SKIPPED，也不是 FAIL）。"""
    steps = [{"tool": "read_file", "arg": "a.md", "success": True}]
    r = _completion_verify(messages=[], tool_steps=steps, session_id="v3", user_id="u", turn_id=1)
    assert r["verdict"] == "NOT_APPLICABLE" and r["checked"] is False


def test_verdict_values_are_closed_set():
    """verdict 取值封闭：PASS / FAIL / NOT_APPLICABLE 三者之一。"""
    src = open("core/gateway/v9_bridge/response_guard.py", encoding="utf-8").read()
    for v in ("PASS", "FAIL", "NOT_APPLICABLE"):
        assert v in src
