# -*- coding: utf-8 -*-
"""2026-09-06 修复2 防回归: 假完成拦截不依赖 content 含✅ 字样。
Agent 输出「还需再查/计划/复述进展」等总结状文本(无✅)但任务要求写入且无实际写入 → 仍拦截。"""
import io

_GW = io.open("core/gateway/completion_guard.py", encoding="utf-8").read()


def test_fake_done_trigger_not_literal_only():
    """拦截触发应含 _resp_looks_done(多个完成措辞) 而非仅 ✅ 字面"""
    assert "_resp_looks_done" in _GW
    assert "任务完成" in _GW and '"已完成"' in _GW
    assert "_needs_fake_check" in _GW


def test_write_task_without_write_intercepted():
    """写类任务(code_modify/delivery)无写入 → 即使 content 无✅ 也进假完成检查"""
    assert "_task_requires_write" in _GW
    assert "not _has_write" in _GW


def test_write_kw_includes_adjust():
    """分类词补充: 调整/落盘/改/统一 → 改草稿类任务归 code_modify"""
    _CV = io.open("core/gateway/context_validator.py", encoding="utf-8").read()
    i = _CV.find("_write_kw = [")
    seg = _CV[i : i + 220]
    assert '"调整"' in seg and '"落盘"' in seg and '"统一"' in seg


def test_vault_write_keywords_detected():
    """用户消息含 write_draft/草稿 → 写意图检测存在(新结构 _user_wants_write_fc)"""
    assert "_user_wants_write_fc" in _GW
    assert "write_draft" in _GW
    assert "_task_requires_write" in _GW
