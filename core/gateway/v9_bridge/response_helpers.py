# -*- coding: utf-8 -*-
"""P3-A 辅助函数归位：v9 桥接响应辅助（从 agent_gateway_enhanced.py 迁入，2026-09-12）。"""


def _build_tool_steps_summary(tool_steps, limit=160):
    """max_tokens 收敛空产出修复: 从 tool_steps 提取产出摘要(不调 LLM)。

    格式: "已完成 N 个工具调用，成功 M 个。关键发现：{最后成功的工具结果摘要}"
    """
    try:
        _ok = [s for s in tool_steps if s.get("success")]
        _sum = f"已完成 {len(tool_steps)} 个工具调用，成功 {len(_ok)} 个。"
        if _ok:
            _last = _ok[-1]
            _finding = str(_last.get("result") or "")[:limit]
            if _finding:
                _sum += f"关键发现：{_finding}"
        return _sum
    except Exception:
        return ""


def _goal_info_for_response(session_id):
    """Goal 驱动多 turn: 组装 goal_info 响应字段(供前端判断是否续跑)。

    turn = goal.history 中唯一 turn_id 数(每次 turn_end → update_goal_progress 追加 1 条)。
    max_turns 从 execution_policy.execution_budget.goal_max_turns 读取(默认 5)。
    """
    try:
        from core.gateway.goal_state import get_goal_by_session_id
        from core.gateway.shared_state import _load_v9_execution_policy

        _g = get_goal_by_session_id(session_id)
        if _g is None:
            # R1: token 字段统一(无 goal 时预算=配置值, used=0)
            _gwater_n = int(
                ((_load_v9_execution_policy() or {}).get("execution_budget", {}) or {}).get(
                    "per_task_token_budget", 500000
                )
                or 500000
            )
            return {
                "goal_active": False,
                "goal_complete": False,
                "goal_done": 0,
                "goal_total": 0,
                "turn": 0,
                "max_turns": int(
                    ((_load_v9_execution_policy() or {}).get("execution_budget", {}) or {}).get("goal_max_turns", 5)
                    or 5
                ),
                "token_budget": _gwater_n,
                "token_used": 0,
                "token_left": _gwater_n,
            }
        _mt = int(((_load_v9_execution_policy() or {}).get("execution_budget", {}) or {}).get("goal_max_turns", 5) or 5)
        # R1(2026-08-30): goal 续跑条件从"轮数<5"改为"累计 token < 预算" —
        # 返回 token_water/token_budget 供前端判断; max_turns 保留为护栏语义(不再硬掐)
        _gwater = int(
            ((_load_v9_execution_policy() or {}).get("execution_budget", {}) or {}).get("per_task_token_budget", 500000)
            or 500000
        )
        _p = _g.get("progress") or {}
        _hist = _g.get("history") or []
        _gused = 0
        for _h in _hist:
            try:
                _gused += int(_h.get("tokens", 0) or 0)
            except Exception:
                pass
        _turns = len({str(h.get("turn_id")) for h in _hist if h.get("turn_id") is not None})
        return {
            "goal_id": _g.get("goal_id", ""),
            "goal_active": _g.get("status") == "active",
            "goal_complete": _g.get("status") in ("complete", "archived"),
            "goal_done": int(_p.get("done", 0) or 0),
            "goal_total": int(_p.get("total", 1) or 1),
            "turn": _turns,
            "max_turns": _mt,
            "token_budget": _gwater,
            "token_used": _gused,
            "token_left": max(_gwater - _gused, 0),
        }
    except Exception:
        return {
            "goal_active": False,
            "goal_complete": False,
            "goal_done": 0,
            "goal_total": 0,
            "turn": 0,
            "max_turns": 5,
            "token_budget": 500000,
            "token_used": 0,
            "token_left": 500000,
        }
