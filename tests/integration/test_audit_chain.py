"""#100 G4: V9 工具循环全量审计 — 队列落盘 / 5s 窗口 / 复核交叉核对"""
import sys, os, time, json
sys.path.insert(0, ".")
import pytest

from core.gateway import audit as _audit


def _reset_queue():
    with _audit._audit_lock:
        _audit._audit_queue = []
    # 备份并清空审计文件（测试用独立文件）
    if _audit._AUDIT_FILE.exists():
        _audit._AUDIT_FILE.unlink()


def test_audit_queue_batch_persist():
    """队列 + 批量落盘：flush 后文件可读，未 flush 的仍在队列"""
    _reset_queue()
    _audit.audit_tool_call("write_file", {"path": "a.py"}, {"success": True}, "u", "aud_s1", 10)
    _audit.audit_tool_call("execute_command", {"command": "python a.py"}, {"success": True}, "u", "aud_s1", 20)
    assert len(_audit._audit_queue) == 2
    _audit.flush_audit()
    assert len(_audit._audit_queue) == 0
    recs = _audit.read_audit_records("aud_s1")
    assert len(recs) == 2
    assert {r["tool"] for r in recs} == {"write_file", "execute_command"}
    assert all(r["success"] for r in recs)


def test_read_merges_queued_records():
    """复核读到的记录含未落盘队列（防批量落盘延迟误判）"""
    _reset_queue()
    _audit.audit_tool_call("read_file", {"path": "a.py"}, {"success": True}, "u", "aud_s2", 5)
    # 不 flush：队列中应有 1 条
    recs = _audit.read_audit_records("aud_s2")
    assert len(recs) == 1, "未 flush 的记录也应被复核读到"


def test_verify_completion_report_matches():
    """复核：声称成功的工具在审计中有对应成功记录 → 通过"""
    _reset_queue()
    _audit.audit_tool_call("write_file", {"path": "a.py"}, {"success": True}, "u", "aud_s3", 10)
    _audit.audit_tool_call("execute_command", {"command": "python a.py"}, {"success": True}, "u", "aud_s3", 20)
    _audit.audit_tool_call("read_file", {"path": "a.py"}, {"success": True}, "u", "aud_s3", 5)
    _audit.flush_audit()
    recs = _audit.read_audit_records("aud_s3")
    report = {
        "write": {"tool": "write_file", "claimed": True},
        "compile": {"tool": "execute_command", "claimed": True},
        "run": {"tool": "execute_command", "claimed": True},
        "content": {"tool": "read_file", "claimed": True},
    }
    res = _audit.verify_completion_report(report, recs)
    assert res["passed"], res["failures"]


def test_verify_fails_on_fake_claim():
    """复核：声称 write_file 成功但审计无记录 → 拦截"""
    _reset_queue()
    _audit.audit_tool_call("read_file", {"path": "a.py"}, {"success": True}, "u", "aud_s4", 5)
    _audit.flush_audit()
    recs = _audit.read_audit_records("aud_s4")
    report = {"write": {"tool": "write_file", "claimed": True}}
    res = _audit.verify_completion_report(report, recs)
    assert not res["passed"]
    assert any("write" in f for f in res["failures"])


def test_window_semantics():
    """5s 窗口：声称时间与审计时间偏差超窗 → 不匹配（防时序误判，也防乱认）"""
    _reset_queue()
    _now = time.time()
    _audit.audit_tool_call("write_file", {"path": "a.py"}, {"success": True}, "u", "aud_s5", 10)
    _audit.flush_audit()
    recs = _audit.read_audit_records("aud_s5")
    # 声称时间在审计前 1000s → 超窗不匹配
    report_far = {"write": {"tool": "write_file", "claimed": True, "ts": _now - 1000}}
    res_far = _audit.verify_completion_report(report_far, recs, window=5)
    assert not res_far["passed"]
    # 声称时间贴近审计时间 → 命中
    _audit_t = recs[0]["ts"]
    report_near = {"write": {"tool": "write_file", "claimed": True, "ts": _audit_t}}
    res_near = _audit.verify_completion_report(report_near, recs, window=5)
    assert res_near["passed"]


def test_cross_check_completion_helper():
    """V9 完成路径 helper：VerificationChain steps → 审计交叉核对"""
    _reset_queue()
    _audit.audit_tool_call("write_file", {"path": "x.py"}, {"success": True}, "u", "aud_s6", 10)
    _audit.audit_tool_call("execute_command", {"command": "python x.py"}, {"success": True}, "u", "aud_s6", 20)
    _audit.audit_tool_call("read_file", {"path": "x.py"}, {"success": True}, "u", "aud_s6", 5)
    _audit.flush_audit()
    vc_ok = {
        "passed": True,
        "steps": {
            "step1_write": {"passed": True},
            "step2_syntax": {"passed": True},
            "step3_run": {"passed": True},
            "step4_content": {"passed": True},
            "step5_done_when": {"passed": True, "detail": "无 done_when 断言，跳过"},
        },
    }
    cc = _audit.cross_check_completion(vc_ok, "aud_s6", task_start_ts=time.time() - 60)
    assert cc["audit_passed"], cc["audit_failures"]


def test_cross_check_blocks_fake():
    """helper 对无审计证据的假完成返回 audit_passed=False"""
    _reset_queue()
    vc_fake = {
        "passed": True,
        "steps": {
            "step1_write": {"passed": True},
            "step2_syntax": {"passed": True},
            "step3_run": {"passed": True},
            "step4_content": {"passed": True},
            "step5_done_when": {"passed": True, "detail": "无 done_when 断言，跳过"},
        },
    }
    cc = _audit.cross_check_completion(vc_fake, "NO_SUCH_SESSION")
    assert not cc["audit_passed"]
    assert cc["audit_failures"]


def test_cross_check_none_vc_degraded():
    """vc=None（降级路径）→ 审计复核不拦截"""
    cc = _audit.cross_check_completion(None, "whatever")
    assert cc["audit_passed"] is True
