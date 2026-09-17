# -*- coding: utf-8 -*-
"""S5 单测: 预算服务(token_stage/load_budget) + 完成判定单点(completion_guard)"""
import sys

sys.path.insert(0, ".")
from core.gateway import budget
from core.gateway.completion_guard import complete_if_valid, detect_sys_echo, detect_transitional, verdict


def test_budget_stage():
    assert budget.token_stage(100, 1000) == "ok"
    assert budget.token_stage(799, 1000) == "ok"
    assert budget.token_stage(800, 1000) == "warn80"
    assert budget.token_stage(1000, 1000) == "water"
    assert budget.token_stage(1200, 1000) == "over"
    assert budget._WARN_RATIO == 0.8 and budget._PER_TASK_BUDGET == 500000


def test_completion_verdict():
    assert detect_transitional("现在确认服务可用性，为构造 prompt 做准备") is True
    assert detect_sys_echo("[系统] 当前阶段：交付。请用 write_file 写入。\n[系统] 当前阶段：交付。") is True
    good = "报告已写入 vault；中文可用、坐标不稳定 → 混合方案结论。"
    v = verdict(good)
    assert v["deliverable"] is True
    assert verdict("下一步先确认可用性再跑")["deliverable"] is False


def test_complete_if_valid_gate():
    """完成判定唯一入口: 不可交付报告 → False(不 complete); 可交付不抛错"""
    assert complete_if_valid("u", "s", report="下一步准备再跑一次") is False
    # 可交付: 内部调 goal_state.complete_goal(无该 session goal 时幂等/异常安全) → 不应抛错
    try:
        complete_if_valid("u_none", "s_none", report="任务完成，报告已交付。")
    except Exception:
        assert False, "不应抛错"
