# -*- coding: utf-8 -*-
"""守卫执行器 — 统一入口(bridge_loop / execute_agent_task 共用)。

run_pre_guards:  顺序执行 pre-execute 守卫(waterfall 短路), 返回首个 deny 或 None
run_post_guards: 执行 post-execute 观察守卫(emit 广播), 结果写 payload["guard_results"]

调用方契约:
  - pre: 先构造 payload{tool,args,user_id,session_id,sandbox_base,messages,...
          approved,tool_call_id,tool_calls_plan,assistant_content,task_id},
         再 run_pre_guards(payload, scope_key); deny 非 None 时按 payload["status"] 分支。
  - post: 工具执行后构造 payload(+result,elapsed_ms,agent_id), run_post_guards;
          观察结果读 payload.get("guard_results", {})。

作用域: 子任务传 scope_key(挂免审批守卫集); 主任务/主聊天传 None(全局, 含审批)。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from core.gateway.guards.base import EVENT_POST_EXECUTE, EVENT_PRE_EXECUTE
from core.gateway.guards.registry import mount_guards
from core.os.context import get_v9_context

# 子任务挂载集(免审批): ⭐ PM 2026-10-04（承 技总 958 §二.⒝ · 老板「批」）：
#   只摘 approval/plan ⇒ ⭐ **留 escape_guard（锚点B · 路径/命令越权确定性拒）**；
#   由：原表「一并摘 escape」＋ `waterfall` 之 scope **只加不减** ⇒ 一「真减」即连锚点B 同摘 ⇒ **无闸**
#   ⚠ 真达之路 ＝ `ApprovalGuard` 读载荷 `sub_task_id` 早返（见 `registry.py`）· ⛔ 靠本表（被全局盖过）
SUBTASK_GUARD_EXCLUDE = ["approval_guard", "plan_guard"]
# 主任务/主聊天全量挂载
FULL_GUARD_EXCLUDE: list = []

_scope_mounted: set = set()  # 已挂载守卫的 scope_key(避免重复 mount)


def ensure_guards_mounted(scope_key: Optional[str] = None, exclude: Optional[list] = None) -> None:
    """确保守卫已挂载(幂等)。主路径挂全局(含审批), 子任务挂 scope(免审批)。"""
    if scope_key is None:
        return  # 全局守卫由网关启动时挂载(见 agent_gateway 初始化)
    if scope_key in _scope_mounted:
        return
    mount_guards(get_v9_context(), scope=scope_key, exclude=exclude if exclude is not None else SUBTASK_GUARD_EXCLUDE)
    _scope_mounted.add(scope_key)


def run_pre_guards(payload: Dict, scope_key: Optional[str] = None, exclude: Optional[list] = None) -> Optional[Dict]:
    """顺序执行 pre-execute 守卫; 返回首个 deny dict 或 None(全部放行)。"""
    if scope_key is not None:
        ensure_guards_mounted(scope_key, exclude)
    return get_v9_context().waterfall(EVENT_PRE_EXECUTE, payload, scope=scope_key)


def run_post_guards(payload: Dict, scope_key: Optional[str] = None, exclude: Optional[list] = None) -> Dict:
    """执行 post-execute 观察守卫; 结果写入 payload["guard_results"] 并返回。"""
    if scope_key is not None:
        ensure_guards_mounted(scope_key, exclude)
    payload.setdefault("guard_results", {})
    get_v9_context().emit(EVENT_POST_EXECUTE, payload, scope=scope_key)
    return payload.get("guard_results", {})


# ===== 批98：判定型代码留痕（体检项 61）=====
# 事故：批97 核对「curl -X POST 到底有没有被拦」时，六个计数（含宽词 guards）**全为 0**，
#   既可能是「没拦」也可能是「拦了但没留痕」—— **不可区分**，方向定不了。
#   同型问题本线程已第三次（批87 截断静默 / 批96 拦截对用户不可见 / 批97 判定静默）。
# 落点选择：加在**唯一分发点** run_pre_guards（体检项 20：规矩加在统一分发上，不散在各守卫里），
#   一处即覆盖全部 pre-guard、且 **deny 与 allow 两个分支都留痕**（体检项 61）。
_orig_run_pre_guards = run_pre_guards


def run_pre_guards(payload, scope_key=None, **kw):
    _r = _orig_run_pre_guards(payload, scope_key, **kw)
    try:
        _pl = payload or {}
        _args = _pl.get("args") or {}
        _cmd = str(_args.get("command", "") or "")[:80]
        _sid = str(_pl.get("session_id", "") or "")
        _tool = str(_pl.get("tool", "") or "")
        if _r:
            print(
                "[GUARD] deny session_id=%s tool=%s status=%s reason=%s cmd=%s"
                % (_sid, _tool, (_r or {}).get("status"), str((_r or {}).get("reason"))[:80], _cmd)
            )
        else:
            print("[GUARD] allow session_id=%s tool=%s cmd=%s" % (_sid, _tool, _cmd))
    except Exception:
        pass
    return _r
