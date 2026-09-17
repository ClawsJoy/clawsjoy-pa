"""write_file 审批确认内容截断修复测试: pending 存完整 content, 确认后执行用 full 而非 preview"""
import sys

sys.path.insert(0, ".")
import pytest


def test_pending_has_full_content():
    """ApprovalGuard pending_write 含完整 content(非仅 preview)"""
    from core.gateway.guards.registry import ApprovalGuard

    g = ApprovalGuard()
    long_content = "行" * 2000  # 超 preview 500 上限
    r = g.check(
        {
            "tool": "write_file",
            "session_id": "s1",
            "tool_call_id": "tc1",
            "args": {"path": "report.md", "content": long_content},
        }
    )
    assert r is not None and r.get("status") == "write_pending"
    pw = r.get("pending_write") or {}
    assert len(pw.get("content", "")) == len(long_content), "pending 应含完整 content"
    assert len(pw.get("content_preview", "")) <= 500, "preview 仍截断给前端"


def test_confirm_uses_full_content_in_source():
    """确认路径 fallback 优先用 pending.content(非 preview)"""
    _SRC = open("core/gateway/approval.py", encoding="utf-8").read()  # P3-A: _resume_bridge_after_approval 已归位
    assert 'if pending.get("content"):' in _SRC, "应优先用完整 content"
    assert '_bargs_wa["content"] = pending["content"]' in _SRC, "确认执行用 full content"
    # preview 降为 fallback
    assert 'pending["content_preview"]' in _SRC
