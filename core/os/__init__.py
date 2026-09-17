# -*- coding: utf-8 -*-
"""ClawsJoy OS 执行上下文包 — Cordis Context 的 Python 简化实现。

P0: 服务容器 + 事件总线 + 作用域 + 插件挂载骨架。
P3: 升格为 OSContext(多版本网关统一底座)。

导出: V9Context / OSContext / V9Scope / V9Plugin / get_v9_context
"""
from core.os.context import V9Context, V9Scope, OSContext, get_v9_context
from core.os.plugin import V9Plugin

__all__ = [
    "V9Context",
    "V9Scope",
    "OSContext",
    "V9Plugin",
    "get_v9_context",
]
