# -*- coding: utf-8 -*-
"""S5(2026-09-05): 预算服务单点 — 阈值/判定唯一来源。

统一 R1 token 水位、L5 80% 预警、400KB 硬截断与单任务预算的口径。
"""
_PER_TASK_BUDGET = 500000      # 单任务 token 预算(execution_policy per_task_token_budget 默认)
_WARN_RATIO = 0.8              # 预警阈值(达预算 80%)
_HARD_BYTES_LIMIT = 400000     # 400KB 硬截断护栏(字符级估算口径, 与原实现一致)


def token_stage(tokens, budget=None):
    """tokens → 阶段: ok / warn80 / water(达到预算) / over。

    单一判定: <80% → ok; 80%..<100% → warn80; ==100% → water; >100% → over。
    """
    b = budget if budget is not None else _PER_TASK_BUDGET
    if tokens >= b:
        return "over" if tokens > b else "water"
    if tokens >= b * _WARN_RATIO:
        return "warn80"
    return "ok"


def load_budget(policy=None):
    """从 execution_policy 读预算(缺失回退默认), 返回 int。"""
    try:
        if policy is None:
            import yaml
            with open("config/v9/execution_policy.yaml", encoding="utf-8") as _f:
                policy = yaml.safe_load(_f) or {}
        return int(((policy.get("execution_budget", {}) or {}).get("per_task_token_budget", 0) or 0) or _PER_TASK_BUDGET)
    except Exception:
        return _PER_TASK_BUDGET
