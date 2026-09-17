"""审批死循环修复测试: 同 session 同文件首次批准后免审"""
import sys

sys.path.insert(0, ".")
import pytest

from core.gateway.shared_state import clear_approved_files, is_file_approved, mark_file_approved


def test_mark_and_check_approved():
    """批准后同文件免审, 不同文件不误放行"""
    clear_approved_files()
    mark_file_approved("sess1", "data/report.md")
    assert is_file_approved("sess1", "data/report.md") is True
    assert is_file_approved("sess1", "data/other.md") is False, "不同文件不误放行"
    assert is_file_approved("sess2", "data/report.md") is False, "不同session不共享"
    clear_approved_files()


def test_clear_approved():
    """清理: 会话级 + 全部"""
    clear_approved_files()
    mark_file_approved("sess1", "a.md")
    mark_file_approved("sess2", "b.md")
    clear_approved_files("sess1")
    assert is_file_approved("sess1", "a.md") is False
    assert is_file_approved("sess2", "b.md") is True
    clear_approved_files()
    assert is_file_approved("sess2", "b.md") is False


def test_approval_guard_bypass_on_approved_file(monkeypatch):
    """ApprovalGuard: 已批准文件即使新 tool_call_id 也放行(不死循环)"""
    from core.gateway.guards.registry import ApprovalGuard

    clear_approved_files()
    g = ApprovalGuard()
    # 首次: 未批准 → write_pending
    r1 = g.check({"tool": "write_file", "session_id": "s1", "tool_call_id": "tc1", "args": {"path": "r.md"}})
    assert r1 is not None and r1.get("status") == "write_pending", "首次应弹审批"
    # 模拟确认后标记批准
    mark_file_approved("s1", "r.md")
    # Agent 重试(新 tool_call_id, 同文件) → 免审放行
    r2 = g.check({"tool": "write_file", "session_id": "s1", "tool_call_id": "tc2", "args": {"path": "r.md"}})
    assert r2 is None, "已批准文件新id应放行(免审)"
    # 不同文件仍弹审批
    r3 = g.check({"tool": "write_file", "session_id": "s1", "tool_call_id": "tc3", "args": {"path": "other.md"}})
    assert r3 is not None and r3.get("status") == "write_pending", "不同文件仍弹审批"
    clear_approved_files()
