# -*- coding: utf-8 -*-
"""工具守卫插件包 — P1 守卫插件化(见 docs/reports/p1_guard_pluginization_plan.md)。

S1: 基座 + 注册表骨架。11 个守卫占位类, 未接任何现有守卫(零行为变化)。
S2+ 逐个实现 check() 并接线到执行路径。
"""
from core.gateway.guards.base import (
    ToolGuard,
    EVENT_PRE_EXECUTE,
    EVENT_POST_EXECUTE,
    EVENT_RESULT,
    ST_WRITE_PENDING,
    ST_PLAN_PENDING,
    ST_ESCALATION_BLOCKED,
    ST_PAUSED,
    ST_FORBIDDEN,
    ST_QUOTA_EXHAUSTED,
    ST_MODE_LIMITED,
)
from core.gateway.guards.registry import (
    GUARD_ORDER,
    QuotaGuard,
    ModeGuard,
    ForcedToolGuard,
    ForbiddenGuard,
    EscapeGuard,
    ApprovalGuard,
    PlanGuard,
    RecursionGuard,
    ReminderGuard,
    AuditGuard,
    FailurePauseGuard,
    get_guard_classes,
    guard_names,
    mount_guards,
    unmount_guards,
)

__all__ = [
    "ToolGuard",
    "EVENT_PRE_EXECUTE",
    "EVENT_POST_EXECUTE",
    "EVENT_RESULT",
    "ST_WRITE_PENDING",
    "ST_PLAN_PENDING",
    "ST_ESCALATION_BLOCKED",
    "ST_PAUSED",
    "ST_FORBIDDEN",
    "ST_QUOTA_EXHAUSTED",
    "ST_MODE_LIMITED",
    "GUARD_ORDER",
    "QuotaGuard",
    "ModeGuard",
    "ForcedToolGuard",
    "ForbiddenGuard",
    "EscapeGuard",
    "ApprovalGuard",
    "PlanGuard",
    "RecursionGuard",
    "ReminderGuard",
    "AuditGuard",
    "FailurePauseGuard",
    "get_guard_classes",
    "guard_names",
    "mount_guards",
    "unmount_guards",
]
