# -*- coding: utf-8 -*-
"""S5(2026-09-05): 预算服务单点 — 阈值/判定唯一来源。

统一 R1 token 水位、L5 80% 预警、400KB 硬截断与单任务预算的口径。
"""
_PER_TASK_BUDGET = 500000      # 单任务 token 预算(execution_policy per_task_token_budget 默认)
WARN_RATIO = 0.8               # 公开 API(承 `初审_187` D3): 预警阈值 —— 语义 = **单任务预算** 的 80%
_WARN_RATIO = WARN_RATIO       # 兼容旧私有名(⛔ 不新增语义 · 同一单源)
CTX_COMPRESS_RATIO = 0.8       # ⚠ 另一语义: **模型上下文窗口**预算的压缩阈值(≠ 单任务预算); 窗口侧两用途(承 初审_220): ① 触发=agent_gateway_enhanced 组装前估算 ② 目标=v9_chat/bridge_call 压缩目标; ⛔ 不写行号(防漂)
_HARD_BYTES_LIMIT = 400000     # 400KB 硬截断护栏(字符级估算口径, 与原实现一致)


def token_stage(tokens, budget=None):
    """tokens → 阶段: ok / warn80 / water(达到预算) / over。

    单一判定: <80% → ok; 80%..<100% → warn80; ==100% → water; >100% → over。
    """
    b = budget if budget is not None else _PER_TASK_BUDGET
    if tokens >= b:
        return "over" if tokens > b else "water"
    if tokens >= b * WARN_RATIO:
        return "warn80"
    return "ok"


def warn_ratio():
    """公开 API(承 `初审_187` D3): 预警阈值(单任务预算口径)。"""
    return WARN_RATIO


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
