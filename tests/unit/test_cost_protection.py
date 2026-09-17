# -*- coding: utf-8 -*-
"""P0 费用保护回归: token 预算 / thinking 按需 / 配置"""
import pathlib
import sys

import yaml

sys.path.insert(0, ".")


def test_policy_has_cost_guards():
    """execution_policy.yaml 含费用保护配置"""
    cfg = yaml.safe_load(open("config/v9/execution_policy.yaml", encoding="utf-8"))
    eb = cfg["execution_budget"]
    assert eb.get("per_task_token_budget") == 500000, eb
    assert eb.get("daily_cost_limit") == 20.0, eb
    assert eb.get("thinking_enabled") is False, eb
    assert eb.get("normal_max_tokens") == 4000, eb
    assert eb.get("thinking_max_tokens") == 8000, eb


def test_thinking_keyword_detection():
    """thinking 按需: 含 分析/推理/设计 关键词才开"""
    # 模拟 v9_agent_chat 的逻辑
    _think_kw = ("分析", "推理", "设计", "规划", "复杂推理", "深度思考", "reasoning", "design")
    assert any(k in "帮我分析这段代码" for k in _think_kw), "含分析应开"
    assert any(k in "设计一个发布流程" for k in _think_kw), "含设计应开"
    assert not any(k in "写个标题" for k in _think_kw), "普通任务不开"


def test_gateway_has_cost_guard_code():
    """agent_gateway_enhanced.py 含费用保护代码"""
    src = open("agent_gateway_enhanced.py", encoding="utf-8").read()
    _bill = open("core/gateway/billing.py", encoding="utf-8").read()
    _budget = open("core/gateway/budget.py", encoding="utf-8").read()
    assert "per_task_token_budget" in _budget, "缺单任务 token 预算(budget)"
    assert "_v9_daily_cost_exceeded" in src, "缺每日费用标记"
    assert "daily_cost_limit" in _bill, "缺每日费用上限(billing)"
    _rec = open("core/gateway/v9_chat/recovery.py", encoding="utf-8").read()  # P3-B: F 块已归位
    assert "thinking_enabled" in _rec, "缺 thinking 开关(recovery)"
    assert "_mt_out = 8000 if _thinking2 else 4000" in src, "缺 max_tokens 动态"
    assert "COST_GUARD" in _bill, "缺 COST_GUARD 日志(billing)"


def test_gateway_compiles():
    """网关语法有效"""
    import ast

    ast.parse(open("agent_gateway_enhanced.py", encoding="utf-8").read())
