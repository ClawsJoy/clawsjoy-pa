"""任务3 v5: 验证链/审计复核修复测试（完全隔离——monkeypatch read_audit_records，不碰 audit 全局状态）"""
import sys, time
sys.path.insert(0, ".")
import pytest
from pathlib import Path

from core.gateway.audit import cross_check_completion


def _fake_records(monkeypatch, tools_success):
    """monkeypatch read_audit_records 返回固定审计记录（避免全量顺序下 audit 全局状态干扰）"""
    import core.gateway.audit as am
    recs = [{"tool": t, "success": True, "ts": time.time(), "session_id": "x"} for t in tools_success]
    monkeypatch.setattr(am, "read_audit_records", lambda *a, **k: list(recs))


def test_cross_check_skips_unevidenced_tools(monkeypatch):
    """复核只核对审计中出现的工具项——compile/run(execute_command 无审计)跳过"""
    _fake_records(monkeypatch, ["write_file", "read_file"])
    vc = {"steps": {
        "step1_write": {"passed": True},
        "step2_syntax": {"passed": True},   # 子任务没跑 execute_command, 审计无记录
        "step3_run": {"passed": True},      # 同上
        "step4_content": {"passed": True},  # read_file 有审计
        "step5_done_when": {"passed": False, "detail": "无断言跳过"},
    }}
    r = cross_check_completion(vc, "s_iso_1", task_start_ts=time.time() - 60)
    assert r["audit_passed"] is True, f"compile/run 无审计应跳过: {r['audit_failures']}"
    assert not r["audit_failures"], f"不应有失败项: {r['audit_failures']}"


def test_cross_check_still_catches_fake_write(monkeypatch):
    """写工具有审计但声称失败(claimed=False)仍应拦截——过滤不放松真实防线"""
    _fake_records(monkeypatch, ["write_file"])
    vc = {"steps": {"step1_write": {"passed": False}}}  # VerificationChain 判未通过
    r = cross_check_completion(vc, "s_iso_2", task_start_ts=time.time() - 60)
    assert r["audit_passed"] is False, "write 声称失败但审计有成功记录应拦截"


def test_cross_check_skip_unseen_content(monkeypatch):
    """content(read_file)声称成功但审计无 read_file -> 过滤跳过(防假完成核心在 write 复核)"""
    _fake_records(monkeypatch, ["write_file"])
    vc = {"steps": {
        "step1_write": {"passed": True},
        "step4_content": {"passed": True},  # 声称读了但审计无 read_file -> 跳过
        "step5_done_when": {"passed": False, "detail": "无断言跳过"},
    }}
    r = cross_check_completion(vc, "s_iso_3", task_start_ts=time.time() - 60)
    assert r["audit_passed"] is True, f"无审计工具项应过滤跳过: {r['audit_failures']}"


def test_evidence_clause_skipped_for_subtask(monkeypatch):
    """规则C(证据条款)在子任务场景跳过——简短回复不误报; 共享任务保持防线"""
    from core.gateway.context_validator import audit_agent_output
    user_msg = "写入文件 output_1.md 内容为: 子任务1输出 值=1。写完后确认完成。"
    short_reply = "已完成"
    # 子任务(skip_evidence=True): 无警告
    w = audit_agent_output(user_msg, short_reply, skip_evidence=True)
    assert not w, f"子任务应跳过规则C: {w}"
    # 共享任务(默认): 规则C 仍触发(简短回复无证据 -> 警告)
    w2 = audit_agent_output(user_msg, short_reply)
    assert w2 and any("证据条款" in x for x in w2), f"共享任务应保留证据条款: {w2}"


def test_content_verify_simple_output(tmp_path):
    """step4 内容核验: 子任务简单输出(指令词过滤后)通过——不复现 v6 死循环"""
    from core.lib.verification_chain import content_verify
    f = tmp_path / "output.md"
    f.write_text("子任务3输出 值=3", encoding="utf-8")
    r = content_verify([{"path": "output.md", "absolute": f}],
                       "请用 write_file 工具写入文件 output_3.md，内容为: 子任务3输出 值=3。写完后确认完成。")
    assert r["passed"] is True, f"简单输出应通过内容核验: {r['failed']}"


def test_content_verify_empty_still_fails(tmp_path):
    """内容核验防线不放松: 空文件仍失败"""
    from core.lib.verification_chain import content_verify
    f = tmp_path / "output.md"
    f.write_text("", encoding="utf-8")
    r = content_verify([{"path": "output.md", "absolute": f}], "写文件 output.md 内容为数据")
    assert r["passed"] is False, "空文件应失败"
    assert any("空" in str(x.get("error", "")) for x in r["failed"]), r["failed"]


def test_collect_written_files_accepts_non_py(tmp_path, monkeypatch):
    """git diff 检测不再限 .py——子任务 md 文件被识别为写入证据"""
    from core.lib.verification_chain import collect_written_files
    workdir = tmp_path / "subtasks" / "sub_x"
    workdir.mkdir(parents=True)
    import subprocess as sp
    def fake_run(cmd, **kw):
        if cmd == ["git", "diff", "--name-only", "HEAD~1", "HEAD"]:
            return sp.CompletedProcess(cmd, 1, stdout="", stderr="")
        if cmd == ["git", "diff", "--name-only", "HEAD"]:
            return sp.CompletedProcess(cmd, 0, stdout="output.md\n", stderr="")
        return sp.run(cmd, **kw)
    monkeypatch.setattr("core.lib.verification_chain.subprocess.run", fake_run)
    (workdir / "output.md").write_text("x", encoding="utf-8")
    written = collect_written_files([], tmp_path, project_root="subtasks/sub_x")
    assert any(w["path"] == "output.md" for w in written), f"md 文件应被识别: {written}"
