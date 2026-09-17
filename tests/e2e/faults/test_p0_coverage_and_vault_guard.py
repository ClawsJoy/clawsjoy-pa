# -*- coding: utf-8 -*-
"""补留痕 + 统一 vault 写守卫回归（2026-09-13）。纪律：先能失败，再能通过。"""
import sys

sys.path.insert(0, ".")
from core.gateway import shared_state as ss
from core.gateway.v9_bridge.tool_runner import _is_vault_write

# ---------- 统一守卫：三条通道 ----------


def test_FAULT_three_channels_are_all_recognized():
    """① 先能失败：三条 vault 写通道都必须被同一条判据认出。"""
    ch1, n1 = _is_vault_write("obsidian_knowledge", {"action": "write_note", "title": "x"})
    ch2, n2 = _is_vault_write("cu_learning", {"action": "persist_sop", "key": "k"})
    ch3, n3 = _is_vault_write("execute_command", {"command": "echo hi >> /mnt/d/Obsidian/ClawsJoy/a.md"})
    assert (ch1, n1) == (True, "obsidian_knowledge")
    assert (ch2, n2) == (True, "cu_learning.persist_sop")
    assert (ch3, n3) == (True, "execute_command")


def test_PASS_readonly_and_sandbox_are_not_blocked():
    """② 再能通过：读操作与沙箱写必须放行（防误伤）。"""
    assert _is_vault_write("obsidian_knowledge", {"action": "read"})[0] is False
    assert _is_vault_write("obsidian_knowledge", {"action": "search", "query": "x"})[0] is False
    assert _is_vault_write("write_file", {"path": "data/reports/a.md"})[0] is False
    assert _is_vault_write("execute_command", {"command": "ls -la data/reports"})[0] is False


def test_sentinel_lifecycle():
    """哨兵：置位→生效；清除→失效。"""
    sid = "s_sent"
    ss.set_continuation(sid, False)
    assert ss.is_continuation(sid) is False
    ss.set_continuation(sid, True)
    assert ss.is_continuation(sid) is True
    ss.set_continuation(sid, False)
    assert ss.is_continuation(sid) is False


def test_guard_only_active_during_continuation():
    """守卫只在续跑期间生效（非续跑期间 vault 写照常）。"""
    src = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "is_continuation" in src and "continuation_blocked" in src


def test_sentinel_set_and_cleared_in_wiring():
    """接线：续跑分支置位、新 turn 清除。"""
    g = open("core/gateway/v9_bridge/response_guard.py", encoding="utf-8").read()
    s = open("core/gateway/v9_chat/bridge_call.py", encoding="utf-8").read()
    assert "set_continuation" in g, "续跑分支未置哨兵"
    assert "set_continuation" in s, "新 turn 未清哨兵"


# ---------- 补留痕：覆盖率 ----------


def test_FAULT_coverage_logging_exists_in_stream_finish():
    """① 先能失败：核验留痕必须在 stream 收尾统一记录（覆盖所有终态出口）。

    此前只在 response_guard 的 normal_complete 一条路径上记 →
    留痕覆盖率仅 9.8%（该覆盖 51 个写类 turn，只记了 5 条），任何阈值都无样本可校。
    """
    src = open("core/gateway/v9_chat/bridge_call.py", encoding="utf-8").read()
    assert "completion_verify" in src, "stream 收尾未记录核验（覆盖率会一直偏低）"
    assert '"stage": "stream"' in src


def test_PASS_lite_mode_skips_heavy_chain(tmp_path, monkeypatch):
    """② 再能通过：lite 版只做 R6，不跑五步链（避免与闸门重复做重活）。"""
    from core.gateway.v9_bridge.response_guard import _completion_verify

    (tmp_path / "deck.md").write_text("正文" * 2000, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("core.lib.gateway_helpers._get_sandbox_base", lambda u, s: str(tmp_path))
    r = _completion_verify(
        messages=[],
        tool_steps=[{"tool": "write_file", "arg": "deck.md", "success": True}],
        session_id="lite1",
        user_id="u",
        turn_id=None,
        lite=True,
    )
    assert r["checked"] is True and r["verdict"] == "PASS"


def test_lite_still_catches_stub(tmp_path, monkeypatch):
    from core.gateway.v9_bridge.response_guard import _completion_verify

    (tmp_path / "artifact_pa_task.txt").write_text("x" * 68, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("core.lib.gateway_helpers._get_sandbox_base", lambda u, s: str(tmp_path))
    r = _completion_verify(
        messages=[],
        tool_steps=[{"tool": "write_file", "arg": "artifact_pa_task.txt", "success": True}],
        session_id="lite2",
        user_id="u",
        turn_id=None,
        lite=True,
    )
    assert r["verdict"] == "FAIL"
