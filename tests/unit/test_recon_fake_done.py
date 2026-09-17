# -*- coding: utf-8 -*-
"""2026-09-06 修复4 防回归: 「侦察后假完成」— 写意图任务只调侦察(read/search)后说完成 → 拦截。
判定改为任务局部扫描(最近 user 之后 tool_calls), 不再用 session 累积 tracker。"""
import io

_GW = io.open("core/gateway/completion_guard.py", encoding="utf-8").read()


def test_task_local_scan_present():
    """应存在任务局部写入扫描: 从最近 user 消息后统计写入/侦察工具"""
    assert "_WRITE_TOOLS_FC" in _GW
    assert "_READ_TOOLS_FC" in _GW
    assert "_fc_task_local_write" in _GW
    assert "_fc_scan" in _GW


def test_write_tools_included():
    """写入类工具含 update_draft/write_draft/write_note/mark_published/write_file"""
    seg = _GW[_GW.find("_WRITE_TOOLS_FC = (") : _GW.find("_WRITE_TOOLS_FC = (") + 300]
    for tool in ("write_draft", "update_draft", "write_note", "write_file", "mark_published"):
        assert tool in seg, tool


def test_read_tools_excluded_from_write():
    """侦察类工具单独归类(obsidian_knowledge/read_file/list_dir 不算写)"""
    assert "obsidian_knowledge" in _GW[_GW.find("_READ_TOOLS_FC") : _GW.find("_READ_TOOLS_FC") + 200]


def test_fake_check_conditions():
    """完成声明但本任务无写入 → 拦截; 写类任务停止无写入 → 拦截"""
    assert "_claimed_done_no_write" in _GW
    assert "_write_task_stopped_no_write" in _GW
    assert "_needs_fake_check = (_claimed_done_no_write or _write_task_stopped_no_write)" in _GW


def test_feedback_mentions_update_draft():
    """拦截反馈应引导 update_draft/write_draft(不只 write_file)"""
    i = _GW.find("你的完成声明被判定为假完成")
    seg = _GW[i : i + 500]
    assert "update_draft" in seg and "write_draft" in seg
