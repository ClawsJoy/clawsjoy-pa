# -*- coding: utf-8 -*-
"""ToolGuard 基类 — 工具守卫插件。

挂载点:
  - "tools/pre-execute"  waterfall: 返回 dict 即拒绝(短路, 后续守卫不执行); None 放行
  - "tools/post-execute" waterfall: 观察守卫(审计/提醒), 返回 None 放行, 附加上下文经 payload 携带

守卫约定:
  - 可拒绝守卫挂 pre-execute, 观察守卫挂 post-execute
  - deny payload 统一形态:
      {"deny": True, "reason": str, "status": str, "error": dict, ...}
    status 取值(状态机透传): write_pending / plan_pending / escalation_blocked /
    paused / forbidden / quota_exhausted / mode_limited / default(硬拒绝)
  - 守卫保持无状态: 状态放 V9Context/V9Scope, 不存实例属性(除 order)

参考: docs/reports/p1_guard_pluginization_plan.md §3.1
"""
from __future__ import annotations
from typing import Any, Dict, Optional

from core.os.plugin import V9Plugin

# 事件名常量(P1 起用, 对齐 Harness tools/* waterfall)
EVENT_PRE_EXECUTE = "tools/pre-execute"
EVENT_POST_EXECUTE = "tools/post-execute"
EVENT_RESULT = "tools/result"

# 状态机透传 status 值
ST_WRITE_PENDING = "write_pending"
ST_PLAN_PENDING = "plan_pending"
ST_ESCALATION_BLOCKED = "escalation_blocked"
ST_PAUSED = "paused"
ST_FORBIDDEN = "forbidden"
ST_QUOTA_EXHAUSTED = "quota_exhausted"
ST_MODE_LIMITED = "mode_limited"


class ToolGuard(V9Plugin):
    """工具守卫基类。

    order: 执行顺序(见 registry.GUARD_ORDER)。在 V9Context.waterfall 中按注册序调用,
    首个返回非 None 者短路。
    event: 挂载事件, 子类覆盖为 EVENT_PRE_EXECUTE(拒绝) 或 EVENT_POST_EXECUTE(观察)。
    """

    name: str = ""
    order: int = 0
    event: str = EVENT_PRE_EXECUTE

    def __init__(self):
        super().__init__()
        self._registered: list = []   # [(event, fn, scope_key_or_None)]

    def apply(self, ctx: Any, scope: Any = None) -> None:
        """挂载: 注册事件监听器, 记录以便 dispose 撤销。scope 非空时挂到该作用域。"""
        self._ctx = ctx
        self._scope = scope
        _sk = scope.key if scope is not None else None
        ctx.on(self.event, self._handler, scope=_sk)
        self._registered.append((self.event, self._handler, _sk))

    def dispose(self) -> None:
        """卸载: 移除已注册的监听器(与 apply 逆序回滚)。"""
        for event, fn, sk in reversed(self._registered):
            try:
                if self._ctx is not None:
                    self._ctx.remove_listener(event, fn, scope=sk)
            except Exception:
                pass
        self._registered.clear()

    def _handler(self, payload: Dict) -> Any:
        """事件处理器: 调用 check, 异常视为放行(守卫不阻断主流程)。"""
        try:
            return self.check(payload)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"[Guard:{self.name}] check 异常(视为放行): {e}")
            return None

    def check(self, payload: Dict) -> Any:
        """守卫逻辑。返回 None=放行; dict=拒绝/观察结果。子类实现。"""
        raise NotImplementedError

    # ---- 便捷构造 ----
    @staticmethod
    def deny(reason: str, status: str = "default", **extra) -> Dict:
        """构造拒绝 payload(挂 pre-execute 的守卫用)。"""
        return {"deny": True, "reason": reason, "status": status, **extra}

    @staticmethod
    def observe(**extra) -> Dict:
        """构造观察结果(挂 post-execute 的守卫用, 不短路, 仅附加信息)。"""
        return {"deny": False, "status": "observed", **extra}

    def __repr__(self) -> str:
        return f"<ToolGuard {self.name} order={self.order} event={self.event}>"
