# -*- coding: utf-8 -*-
"""插件基类 — 对齐 Cordis plugin.apply(ctx)。

生命周期:
  apply(ctx[, scope])  挂载时调用: 注册服务/监听器/挂子插件
  dispose()            卸载时调用: 逆序回滚 apply 的注册(释放资源)

约定:
  - apply 内通过 ctx.on/provide 注册的所有东西, dispose 必须撤销
  - 插件应保持无状态(状态放 ctx/scope)
"""
from __future__ import annotations
from typing import Any, Optional


class V9Plugin:
    """所有插件基类。"""

    name: str = ""

    def __init__(self):
        self._ctx: Any = None
        self._scope: Any = None

    def apply(self, ctx: Any, scope: Any = None) -> None:
        """挂载钩子。子类覆盖。ctx=V9Context, scope=V9Scope 或 None。"""
        raise NotImplementedError

    def dispose(self) -> None:
        """卸载钩子。子类覆盖(逆序回滚 apply 的注册)。默认空操作。"""

    def __repr__(self) -> str:
        return f"<V9Plugin {self.name or type(self).__name__}>"
