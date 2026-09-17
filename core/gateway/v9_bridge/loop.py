# -*- coding: utf-8 -*-
"""V9 桥接循环编排骨架（P2 拆解）。

只留编排骨架（轮循环 + 退出点 + 控制流），业务逻辑归位各自模块。
S7 函数头初始化归位到本模块 _init_bridge_state。
"""

import time
from pathlib import Path


def _check_v9_capability(messages, tools, session_id, user_id):
    """P1-2 能力边界检查: 任务需要网络工具但当前模式/工具池不支持 → 提前返回明确错误(不浪费轮次)。

    判定:
      - 任务含网络意图关键词(新闻/搜索/网页/资讯/抓取/最新/动态/网址/链接...)
      - 且 LLM 工具池或模式白名单均无 fetch_web/browse_web → 无法完成
    只读任务(无网络关键词)零影响; 写任务照常走审批。
    返回 dict(final_resp) 或 None。
    """
    try:
        from core.gateway.quota_manager import get_mode, get_mode_tools
        from core.lib.gateway_helpers import last_user_task_msg

        _task = last_user_task_msg(messages)
        if not _task:
            return None
        _net_kw = (
            "新闻",
            "搜索",
            "网页",
            "资讯",
            "抓取",
            "最新",
            "动态",
            "网址",
            "链接",
            "news",
            "search",
            "web",
            "fetch",
            "browse",
            "资讯站",
        )
        if not any(k in _task for k in _net_kw):
            return None
        _tool_names = [t.get("function", {}).get("name", "") for t in (tools or [])]
        _mode = get_mode(session_id, _task)
        _mode_tools = get_mode_tools(session_id, _task)
        _net_available = any(t in ("fetch_web", "browse_web") for t in _tool_names) and any(
            t in ("fetch_web", "browse_web") for t in _mode_tools
        )
        if _net_available:
            return None
        return {
            "success": False,
            "capability_blocked": True,
            "error": "当前模式不支持网络访问，无法完成信息收集任务。请切换模式或使用支持网络的部署。",
            "mode": _mode,
            "reason_detail": "网络工具(fetch_web/browse_web)未在当前模式开放",
        }
    except Exception:
        return None


def _init_bridge_state(*, messages, tools, user_id, session_id, model, _thinking2, on_round):
    """桥接循环初始化（S7，从 _v9_bridge_loop 归位）。

    契约：纯初始化，返回 state dict。除 side-effect（tmp 清理 / on_round(-1) / turn_start /
    任务边界写入 / followup 消费）外不碰循环逻辑。返回的 _cap_block 若非 None，调用方需立即早退。

    返回 dict 键：messages(经 followup 重绑) / tokens / data_resp / _is_7b_fallback /
    _tool_steps / _bridge_exhausted / _task_start_ts / _max_total_tools / _max_bridge_rounds /
    _water_tok / _no_think / _turn_id / _cap_block。
    """
    _task_start_ts = time.time()
    tokens = 0
    data_resp = None
    _is_7b_fallback = False  # 7B 降级标记：跳过压缩
    _tool_steps = []
    _bridge_exhausted = True
    # data/tmp 自动清理(2026-08-30): 每次任务开始清掉 >24h 的临时调试脚本/缓存
    # 防 Agent 反复试错堆积 98 个文件(污染 list_dir 结果 + 上下文预算)
    try:
        import time as _t_tmp
        from pathlib import Path as _Pt

        _tmp_root = _Pt("data/tmp")
        if _tmp_root.exists():
            _now_tmp = _t_tmp.time()
            for _tf in list(_tmp_root.iterdir()):
                try:
                    if _tf.is_file() and _now_tmp - _tf.stat().st_mtime > 86400:
                        _tf.unlink()
                except Exception:
                    pass
    except Exception:
        pass
    # 任务2 流式: 初始事件（任务开始）
    if on_round is not None:
        try:
            on_round(-1, list(_tool_steps), "任务开始执行")
        except Exception:
            pass

    # #21 总工具数硬上限(execution_policy.yaml max_total_tools, 默认 32)
    try:
        from core.gateway.shared_state import _load_v9_execution_policy

        _max_total_tools = int(
            ((_load_v9_execution_policy() or {}).get("execution_budget", {}) or {}).get("max_total_tools", 32) or 32
        )
    except Exception:
        _max_total_tools = 32

    # P2b 修复(2026-08-29 → 2026-09-07): 任务边界写入 — 任务死循环根因修复
    # 原「与投影最后 user 比较、连续重复去重」会吞掉同文本重试:
    # 上次任务失败(空回复) → 用户重发同一任务 → 写入被跳过 → derive(last_task_only)
    # 无新边界 → 投影重放上次失败现场 → 模型继续失败 → 死循环 + token 烧穿。
    # 架构修复:
    #   1) 内部注入消息("[系统]" 前缀: goal 续跑/steer/环境指引) 记 source=runtime_context
    #      (role=system), 模型可见但不推进任务边界;
    #   2) 真实用户消息一律写入(仅 15s 内同内容紧邻去重 — 防同一 POST 被双写, 不误伤重试)。
    try:
        import time as _b_time

        from core.gateway.session_log import EV_USER_MESSAGE as _EV_UM_B
        from core.gateway.session_log import get_session_log

        _b_slog = get_session_log(session_id)
        _b_last_user = None
        for _bm_r in reversed(messages):
            if _bm_r.get("role") == "user" and _bm_r.get("content"):
                _b_last_user = _bm_r
                break
        if _b_last_user is not None:
            _b_utxt = str(_b_last_user.get("content", ""))
            if _b_utxt.startswith("[系统]"):
                _b_slog.append("user_message", {"role": "system", "content": _b_utxt, "source": "runtime_context"})
            else:
                _b_recent_same = False
                _b_now_t = _b_time.time()
                for _bev_r in reversed(_b_slog.events()):
                    if _bev_r.type == _EV_UM_B and _bev_r.payload.get("source") == "user_input":
                        if _bev_r.payload.get("content") == _b_utxt and (_b_now_t - float(_bev_r.ts or 0)) < 15:
                            _b_recent_same = True
                        break
                if not _b_recent_same:
                    _b_slog.append("user_message", {"role": "user", "content": _b_utxt, "source": "user_input"})
    except Exception:
        pass

    # P0 inbox: turn 开始消费 followup 通道(老板跨 turn 追加指示 → 本 turn 最新 user 指令)
    try:
        from core.gateway.shared_state import drain_followup

        _followups = drain_followup(session_id)
        if _followups:
            for _fu in _followups:
                print(f"[FOLLOWUP_INJECT] {str(_fu)[:80]}")
            messages = messages + [{"role": "user", "content": str(_f)[:2000]} for _f in _followups]
    except Exception:
        pass

    # Turn 协议 Step2: turn_start
    try:
        from core.gateway.session_log import log_event as _log_turn

        _turn_id = int(time.time())
        from core.gateway.turn_protocol import write_turn_start as _wt_start

        _wt_start(session_id, _turn_id, str((messages[0].get("content") if messages else ""))[:80])
    except Exception:
        _turn_id = 0

    # P1-2 能力边界检查: 网络任务但模式不支持 → 提前返回明确错误(不浪费工具轮次)
    _cap_block = None
    try:
        _cap_block = _check_v9_capability(messages, tools, session_id, user_id)
    except Exception:
        pass

    # R1(2026-08-30 架构根治): 轮次上限改为 token 水位驱动 — 不再按轮次硬截断。
    try:
        from core.gateway.shared_state import _load_v9_execution_policy as _lv9r

        _max_bridge_rounds = int(
            ((_lv9r() or {}).get("execution_budget", {}) or {}).get("max_bridge_rounds", 100) or 100
        )
    except Exception:
        _max_bridge_rounds = 100
    # R1: token 水位预算(默认 50 万 token, 与 P0 费用保护同一配置键)
    try:
        from core.gateway.shared_state import _load_v9_execution_policy as _lv9w

        _water_tok = int(
            ((_lv9w() or {}).get("execution_budget", {}) or {}).get("per_task_token_budget", 500000) or 500000
        )
    except Exception:
        _water_tok = 500000

    # (2026-09-05 封面类空回复修复): reasoning-only 残留 — 简单生成类任务(封面/写稿/出图等,
    # 无 分析/设计/排查 关键词)直接关 thinking, 防 output=空 reasoning=4000 判空;
    # 空回复重试亦强制关 thinking(见下方分支)。
    _no_think = False
    try:
        _first_usr_s5 = ""
        for _m0 in messages:
            if _m0.get("role") == "user":
                _first_usr_s5 = str(_m0.get("content") or "")
                break
        _gen_kw = ("封面", "生成", "写稿", "写文章", "绘图", "出图", "导出", "渲染", "图片", "海报")
        _think_kw = ("分析", "评估", "设计", "排查", "修复", "架构", "方案", "复盘")
        if (
            _thinking2
            and _first_usr_s5
            and any(k in _first_usr_s5 for k in _gen_kw)
            and not any(k in _first_usr_s5 for k in _think_kw)
        ):
            _no_think = True
            print("[NO_THINK] 简单生成类任务, 关闭 thinking 防 reasoning-only 空回复")
    except Exception:
        pass

    return {
        "messages": messages,
        "tokens": tokens,
        "data_resp": data_resp,
        "_is_7b_fallback": _is_7b_fallback,
        "_tool_steps": _tool_steps,
        "_bridge_exhausted": _bridge_exhausted,
        "_task_start_ts": _task_start_ts,
        "_max_total_tools": _max_total_tools,
        "_max_bridge_rounds": _max_bridge_rounds,
        "_water_tok": _water_tok,
        "_no_think": _no_think,
        "_turn_id": _turn_id,
        "_cap_block": _cap_block,
    }


def _token_water_guard(*, tokens, water_tok, budget_warned80, bmsg):
    """S6-E 收敛守卫：预算 80% 预警 + token 软水位收敛注入（原地改 bmsg）。

    契约：返回 dict {budget_warned80, token_water_hit}。
    token_water_hit=True 时调用方 break 并置 _bridge_exhausted=False（正常收尾，非耗尽/非中断）。
    """
    try:
        # L5(2026-09-05 预算预警): 达预算 80% 注入收敛提示(不中断, 让 Agent 提前收尾)
        from core.gateway.budget import _WARN_RATIO as _wr_s5

        _warn80_tok = int(water_tok * _wr_s5)
        if not budget_warned80 and tokens >= _warn80_tok:
            budget_warned80 = True
            _wtr80 = "[预算预警] token 已消耗 %d(>= 预算 %d 的 80%%)。请立即收敛：" "不再做新的侦察/重读/重试，基于现有结果完成剩余步骤并输出最终结论。" % (
                tokens,
                water_tok,
            )
            bmsg["content"] = (bmsg.get("content") or "") + chr(10) + chr(10) + _wtr80
            print(f"[BUDGET_WARN80] tokens {tokens} >= {_warn80_tok}(预算 80%), 注入收敛预警")
        if tokens >= water_tok:
            _wtr_hint = f"[系统] 任务 token 消耗 {tokens} 已达预算 {water_tok}。" f"请基于已完成的操作直接输出最终总结/结论，不要再调用新工具。"
            bmsg["content"] = (bmsg.get("content") or "") + chr(10) + chr(10) + _wtr_hint
            print(f"[R1_TOKEN_WATER] tokens {tokens} >= 预算 {water_tok}, 注入收敛并正常收尾")
            return {"budget_warned80": budget_warned80, "token_water_hit": True}
    except Exception:
        pass
    return {"budget_warned80": budget_warned80, "token_water_hit": False}
