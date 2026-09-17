# -*- coding: utf-8 -*-
"""P0 费用保护审核修复回归"""
import sys

sys.path.insert(0, ".")
import pytest

_SRC = open("agent_gateway_enhanced.py", encoding="utf-8").read()


def test_today_cost_cached_increment():
    """修复1: 每日费用用全局缓存增量, 不全量遍历 billing"""
    assert "_v9_today_cost" in _SRC, "缺今日费用缓存"
    assert "_v9_today_cost_day" in _SRC, "缺日期缓存"
    _bill = open("core/gateway/billing.py", encoding="utf-8").read()
    assert "for _line in _bfh" not in _bill, "记账块仍全量遍历 billing"


def test_cost_uses_ledger_return():
    """修复2: 每日费用用 ledger 返回的 cost(与扣费一致) — 记账已归位 billing"""
    _bill = open("core/gateway/billing.py", encoding="utf-8").read()
    assert '_rec.get("cost"' in _bill, "未用 ledger 返回 cost"
    assert "(tokens / 1000.0) * 0.001" not in _bill, "仍用手写公式"


def test_budget_limit_success_false():
    """修复3(R1 2026-08-30): budget_limit 改为正常收尾 — success=True + token_water 状态
    (原 success=False 前端显示失败, 实际任务已完成大半 → 伪失败重复计费)。S6-C 归位 response_guard"""
    _RG = open("core/gateway/v9_bridge/response_guard.py", encoding="utf-8").read()
    assert '"success": True, "status": "token_water"' in _RG, "budget_limit 应 success=True + token_water"
    assert '"success": False, "status": "budget_limit"' not in _RG, "不应残留 success=False budget_limit"
