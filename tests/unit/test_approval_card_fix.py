"""审批卡片重复/点无效 修复测试: 前端按钮作用域 + 后端确认标记 + 重复读止损"""
import sys

sys.path.insert(0, ".")
import pytest


def test_frontend_btn_scope_card_only():
    """前端: 确认按钮只禁用当前卡片(非全部)"""
    _SRC = open("web/static/js/approval.js", encoding="utf-8").read()
    assert "card.querySelectorAll('#writeApproveBtn,#writeRejectBtn')" in _SRC, "应只禁用当前卡片按钮"
    assert "document.querySelectorAll('#writeApproveBtn" not in _SRC, "不应禁用全部按钮"


def test_backend_approve_marks_file_approved():
    """后端: 确认即标记文件已批准(即使执行失败也免审后续同文件write)"""
    _SRC = open("core/gateway/approval.py", encoding="utf-8").read()  # P3-A: _resume_bridge_after_approval 已归位
    assert "确认即标记文件已批准" in _SRC, "应有确认标记注释"
    assert "mark_file_approved(session_id, _ap_path)" in _SRC, "确认应调 mark_file_approved"


def test_dup_read_stop_in_source():
    """重复读同一文件止损: 连续3次同路径 → 提示收敛"""
    _SRC = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "dupread_" in _SRC, "应有重复读计数 key"
    assert "重复读取" in _SRC or "重复读" in _SRC, "应有重复读提示文案"
    # 2026-08-30 v3: 计数改 dict(n/ts 时间窗), 阈值仍是 3 次
    assert '["n"] >= 3' in _SRC or "_dup_hist[_dup_path] >= 3" in _SRC, "阈值应为3次"
