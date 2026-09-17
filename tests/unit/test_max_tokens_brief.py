# -*- coding: utf-8 -*-
"""LLM max_tokens 动态(2026-08-29 P0 费用保护): 普通 4000 / thinking 8000"""
import sys

sys.path.insert(0, ".")
import pytest

_SRC = open("agent_gateway_enhanced.py", encoding="utf-8").read()


def test_bridge_loop_max_tokens_dynamic():
    """主桥接调用 max_tokens 动态: 普通 4000, thinking 8000"""
    assert "_mt_out = 8000 if _thinking2 else 4000" in _SRC, "缺动态 max_tokens"


def test_retry_path_uses_dynamic():
    """重试路径复用 _mt_out 动态"""
    # (2026-09-05) thinking 增加 _no_think 门控(简单生成/空回复重试关 thinking)
    assert "max_tokens=_mt_out, thinking=(_thinking2 and not _no_think)" in _SRC


def test_thinking_param_preserved():
    """thinking 参数保留(降本默认关, 复杂任务开)"""
    _LOOP = open("core/gateway/v9_bridge/loop.py", encoding="utf-8").read()
    assert "thinking=(_thinking2 and not _no_think)" in _SRC
    assert (
        "thinking_enabled" in open("core/gateway/v9_chat/recovery.py", encoding="utf-8").read()
    ), "缺 thinking 配置开关(F 块已归位)"
    assert "_think_kw" in _LOOP, "缺 thinking 关键词判断"
    assert "_gen_kw" in _LOOP, "缺简单生成类关键词组"


def test_cost_guard_present():
    """费用保护代码存在(记账已归位 billing)"""
    _bill = open("core/gateway/billing.py", encoding="utf-8").read()
    assert "COST_GUARD" in _bill
    assert "_v9_daily_cost_exceeded" in _SRC
