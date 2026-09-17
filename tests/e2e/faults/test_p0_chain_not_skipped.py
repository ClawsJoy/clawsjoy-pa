# -*- coding: utf-8 -*-
"""五步链「没被跳过」+ ②③ 通道断言（2026-09-13）。

事故：base_dir 契约是「沙箱的父目录」，调用方传了沙箱本身 →
路径双拼 .../clawsjoy_dev/clawsjoy_dev → 抛错被 except 吞 → 五步链从接入至今一次没跑成。
教训：**测试不能只断言 verdict，必须断言「这一步真的跑了」。**
"""
import sys

sys.path.insert(0, ".")
from core.gateway.v9_bridge.response_guard import _completion_verify


def _steps(path):
    return [{"tool": "write_file", "arg": path, "success": True, "round": 1}]


def test_FAULT_chain_must_not_be_silently_skipped(tmp_path, monkeypatch):
    """① 先能失败：五步链必须**真的跑**（chain_ran=True），不能静默跳过。"""
    sb = tmp_path / "clawsjoy_dev"
    (sb / "data" / "reports").mkdir(parents=True)
    (sb / "data" / "reports" / "deck.md").write_text("正文" * 2000, encoding="utf-8")
    monkeypatch.chdir(sb)
    monkeypatch.setattr("core.lib.gateway_helpers._get_sandbox_base", lambda u, s: str(sb))
    msgs = [{"role": "assistant", "content": "已完成：data/reports/deck.md 已写入。"}]
    r = _completion_verify(
        messages=msgs, tool_steps=_steps("data/reports/deck.md"), session_id="c1", user_id="u", turn_id=1
    )
    assert "chain_ran" in r, "返回值必须暴露「五步链是否跑了」"
    assert r["chain_ran"] is True, "五步链被跳过了：%s" % r.get("chain_skip_reason")


def test_PASS_no_double_project_root(tmp_path, monkeypatch):
    """base_dir 传沙箱本身也不得双拼 project_root（函数侧加固）。"""
    from pathlib import Path

    from core.lib.verification_chain import _resolve_sandbox_path

    sandbox = tmp_path / "clawsjoy_dev"
    sandbox.mkdir()
    p = _resolve_sandbox_path(sandbox, "data/reports/x.md")
    assert "clawsjoy_dev/clawsjoy_dev" not in str(p), p
    assert str(p).endswith("clawsjoy_dev/data/reports/x.md"), p


def test_PASS_parent_dir_still_works(tmp_path, monkeypatch):
    """不回归：按契约传父目录仍正确拼出沙箱内路径。"""
    from core.lib.verification_chain import _resolve_sandbox_path

    parent = tmp_path
    (tmp_path / "clawsjoy_dev").mkdir()
    p = _resolve_sandbox_path(parent, "data/reports/x.md")
    assert str(p).endswith("clawsjoy_dev/data/reports/x.md"), p


def test_lite_mode_reports_chain_not_run(tmp_path, monkeypatch):
    """lite 版明确标注未跑五步链（避免把它误当「跑过了」）。"""
    (tmp_path / "deck.md").write_text("正文" * 2000, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("core.lib.gateway_helpers._get_sandbox_base", lambda u, s: str(tmp_path))
    r = _completion_verify(
        messages=[], tool_steps=_steps("deck.md"), session_id="c2", user_id="u", turn_id=None, lite=True
    )
    assert r["chain_ran"] is False and r["verdict"] == "PASS"


# ---------- ②③ 通道：单测断言（端到端造不出来，如实标注） ----------


def test_channel2_cu_learning_persist_sop():
    """② cu_learning.persist_sop（直调 write_vault_note，绕过 ①）。"""
    from core.gateway.v9_bridge.tool_runner import _VAULT_MARKERS, _is_vault_write

    assert _is_vault_write("cu_learning", {"action": "persist_sop", "key": "k"})[0] is True
    assert _is_vault_write("cu_learning", {"sop_key": "x", "content": "y"})[0] is True
    # 判据依赖 vault 根路径标记存在
    assert any("Obsidian" in m for m in _VAULT_MARKERS)


def test_channel3_execute_command_with_vault_path():
    """③ execute_command 含 vault 根路径（security.py 的 _SYS_ESCAPE_PATTERNS 不含 /mnt，不拦）。"""
    from core.gateway.v9_bridge.tool_runner import _is_vault_write

    for cmd in (
        "echo x >> /mnt/d/Obsidian/ClawsJoy/a.md",
        "cp a.md /mnt/d/obsidian/x/y.md",
        'python3 -c \'open("/mnt/d/Obsidian/ClawsJoy/b.md","w")\'',
    ):
        assert _is_vault_write("execute_command", {"command": cmd})[0] is True, cmd
    assert _is_vault_write("execute_command", {"command": "ls -la /tmp"})[0] is False
