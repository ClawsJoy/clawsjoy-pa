# -*- coding: utf-8 -*-
"""P3-A 记账（从 _v9_bridge_loop 归位，2026-09-12）。"""


def _record_cost_round(*, tokens, model, user_id, today_cost, today_cost_day, daily_cost_exceeded):
    """P3-A 记账：record_cost + 今日累计 + 每日上限标记。

    契约：返回 (today_cost, today_cost_day, daily_cost_exceeded)。
    调用方从 main globals 读入/写回(_v9_today_cost/_v9_today_cost_day/_v9_daily_cost_exceeded)。
    """
    from datetime import datetime

    # 记账 + P0 费用保护(每日上限 + 成本日志)
    try:
        from core.gateway.shared_state import _load_v9_execution_policy as _l9p3
        from core.lib.v8.ledger import ledger

        _eb3 = (_l9p3() or {}).get("execution_budget", {}) or {}
        _daily_limit = float(_eb3.get("daily_cost_limit", 20.0) or 20.0)
        _rec = ledger.record_cost(
            server_id="default",
            agent_name=f"agent_{user_id}",
            position="Agent工作区",
            model=model,
            tokens=tokens,
            unit_price=0.001,
            task_id=user_id,
            summary=f"Agent工作区调用 - tokens={tokens}",
        )
        # 当日累计费用: 用 ledger 返回的实际 cost + 全局缓存增量(避免全量遍历 billing)
        _rec_cost = 0.0
        try:
            _rec_cost = float(_rec.get("cost", 0) or 0)
        except Exception:
            _rec_cost = 0.0
        _today_str_now = datetime.now().strftime("%Y-%m-%d")
        _cached_day = today_cost_day
        if _cached_day != _today_str_now:
            # 日期变化 → 重置今日累计
            today_cost = 0.0
            today_cost_day = _today_str_now
        _today_cost = float(today_cost or 0.0) + _rec_cost
        today_cost = _today_cost
        print(
            f"[COST_LOG] model={model} tokens={tokens} cost={_rec_cost:.4f} 今日累计={_today_cost:.2f}/{_daily_limit} task={user_id}"
        )
        # 每日费用上限: 超限标记(下次任务走 7B)
        if _today_cost > _daily_limit:
            daily_cost_exceeded = True
            print(f"[COST_GUARD] 今日费用 {_today_cost:.2f} 超上限 {_daily_limit}, 后续任务走 7B 降级")
            try:
                from core.gateway.sandbox_util import notify_boss

                notify_boss(
                    event_type="cost_limit",
                    message=f"DeepSeek 今日费用 {_today_cost:.2f} 超上限 {_daily_limit}",
                    detail=f"tokens={tokens}",
                    level="warn",
                )
            except Exception:
                pass
    except Exception as e:
        print(f"[V9] 记账失败: {e}")
    return today_cost, today_cost_day, daily_cost_exceeded
