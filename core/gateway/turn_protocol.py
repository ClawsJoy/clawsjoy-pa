"""Turn 协议统一层: reason 计算 + 事件写入(事件溯源核心)。

bridge_loop(agent_gateway_enhanced) 与 execute_agent_task 共用:
  - _compute_turn_reason: reason/detail 单一事实来源(不再各写一套 if 链)
  - write_turn_start/step_start/step_end/turn_end: EV_ 常量写入(防字面量漂移)
"""
from core.gateway.session_log import EV_STEP_END, EV_STEP_START, EV_TURN_END, EV_TURN_START, log_event


def _compute_turn_reason(
    *,
    cancelled=False,
    guard_paused=False,
    exhausted_no_output=False,
    round_exhausted=False,
    bridge_exhausted=False,
    empty_reply_count=0,
    content="",
):
    """Turn 协议 Step1: 计算 reason + reason_detail。

    优先级(与 bridge/exec 现状逐字一致):
      paused(连续失败暂停) > cancelled(协作取消) > error(耗尽且无产出)
      > max_tokens(轮次/工具上限) > need_more(连续空回复) > completed
    """
    if guard_paused:
        return "paused", "连续失败 8 次，任务已暂停，等待老板决策"
    if cancelled:
        return "cancelled", "协作取消(用户停止)"
    if round_exhausted or bridge_exhausted:
        if exhausted_no_output:
            return "error", "无工具产出，任务未完成"
        return "max_tokens", "已达轮次/工具上限"
    if empty_reply_count >= 2 and not str(content or "").strip():
        return "need_more", "模型连续空回复，请重试或调整任务描述"
    return "completed", "assistant 有内容且无待执行 tool_calls"


def write_turn_start(session_id, turn_id, task_name="", path=""):
    """写 turn_start 事件(EV_TURN_START 常量)"""
    log_event(
        session_id,
        EV_TURN_START,
        {"turn_id": turn_id, "task_name": str(task_name or "")[:80], "path": path},
        turn_id=turn_id,
        step_id=0,
    )


def write_step_start(session_id, turn_id, step_id, round_no=None):
    """写 step_start 事件(EV_STEP_START 常量)"""
    payload = {"turn_id": turn_id, "step_id": step_id}
    if round_no is not None:
        payload["round"] = round_no
    log_event(session_id, EV_STEP_START, payload, turn_id=turn_id, step_id=step_id)


def write_step_end(session_id, turn_id, step_id):
    """写 step_end 事件(EV_STEP_END 常量)"""
    log_event(session_id, EV_STEP_END, {"turn_id": turn_id, "step_id": step_id}, turn_id=turn_id, step_id=step_id)


def write_turn_end(session_id, turn_id, reason, detail, tools_n=0, tokens=0, goal_info=None):
    """写 turn_end 事件(EV_TURN_END 常量, 附 reason/detail/goal)"""
    payload = {"turn_id": turn_id, "reason": reason, "reason_detail": detail, "tools": tools_n, "tokens": tokens}
    if goal_info:
        payload.update(goal_info)
    log_event(session_id, EV_TURN_END, payload, turn_id=turn_id, step_id=max(0, int(tools_n)))


def _write_turn_end(
    session_id, turn_id, tokens, reason, detail, tools_n=0, report=None, messages=None, tool_steps=None
):
    """Turn 协议 Step2+3: 写 turn_end 事件 + 审计接入(ledger timeline, 前端审计面板可查看)。

    P1: turn_end 关联 goal — 事件带 goal_id + progress delta; progress 随轮推进
    (reason=completed → done 补齐 total + goal 置 complete; 其余 → done += 本轮工具数)

    报告持久化: report(最终 LLM 总结 / max_tokens tool_steps 摘要)写入 goal 记录 —
    供 /v9/goal/history 跨设备/换浏览器恢复; 同时附到 turn_end 审计事件(截断)。
    """
    _goal_info = {}
    try:
        from core.gateway.goal_state import (
            complete_goal,
            get_goal_by_session_id,
            update_goal_progress,
            update_goal_report,
        )

        _g = get_goal_by_session_id(session_id)
        if _g:
            _gid = _g.get("goal_id")
            _p = _g.get("progress") or {}
            _prev = int(_p.get("done", 0) or 0)
            _total = int(_p.get("total", 1) or 1)
            # 2026-09-03 假完成防护: 过渡语检测(report 短且含准备/将做等词)提前 —
            # 影响 delta: 过渡语场景 done 只加本轮工具数, 不补满 total(progress 不跳 100%)
            _is_transitional = False
            _is_sys_echo = False
            if reason == "completed" and report:
                _r_low = str(report).lower()
                if len(str(report)) < 120 and any(
                    k in _r_low for k in ("准备", "将要做", "接下来", "确认可用", "做准备", "先读", "先确认", "下一步", "再跑")
                ):
                    _is_transitional = True
                # R15(2026-09-03): 系统回声假完成防护 — 最终 report 只是复读系统阶段提示
                # (如 2x"[系统] 当前阶段：交付。请用 write_file 或 python3 heredoc..." 无任何实质产出)
                # → 折叠进过渡语判定: done 只加本轮工具数、不置 complete, 任务保持 active 可续跑
                # (qwen2.5vl 报告任务: Agent summarize 被截断后把系统"交付"提示复读两遍当报告 → 被误判 completed)
                if not _is_transitional:
                    try:
                        import re as _re_r15

                        _rep_r15 = str(report)
                        if "[系统]" in _rep_r15 or "当前阶段" in _rep_r15:
                            _stripped_r15 = _re_r15.sub(r"\[系统\][^\n]*", "", _rep_r15)
                            _stripped_r15 = _re_r15.sub(r"当前阶段[：:][^\n]*", "", _stripped_r15)
                            _stripped_r15 = _re_r15.sub(r"\s+", " ", _stripped_r15).strip()
                            if len(_stripped_r15) < 60:
                                _is_sys_echo = True
                                _is_transitional = True
                    except Exception:
                        pass
            _delta = tools_n if (reason != "completed" or _is_transitional) else max(_total - _prev, 0)
            _new_done = _prev + _delta
            # R1(2026-08-30): 每 turn 记录 tokens 到 goal history(供 token_used 续跑判断)
            try:
                _g_hist = _g.get("history") or []
                for _h in _g_hist:
                    if str(_h.get("turn_id")) == str(turn_id):
                        _h["tokens"] = tokens
                        break
                else:
                    _g_hist.append({"turn_id": turn_id, "tokens": tokens})
                _g["history"] = _g_hist
            except Exception:
                pass
            # 报告落盘(不依赖完成状态): 阶段性/最终报告都持久化
            if report:
                update_goal_report(_g.get("user_id") or "", session_id, report)
            # 跨 session 记忆: 任务完成 → 报告摘要沉淀 known_patterns(用户级)
            if reason == "completed" and report and _g.get("user_id"):
                try:
                    from core.gateway.memory import remember_pattern as _mem_pattern

                    _mem_pattern(_g.get("user_id"), str(report)[:160])
                except Exception:
                    pass
            # progress 始终随 turn 推进(即使 ✅ 路径已先 complete); complete_goal 仅对 active/paused 幂等调用
            update_goal_progress(
                _g.get("user_id") or "",
                session_id,
                done=_new_done,
                step=f"turn{turn_id} tools{tools_n}",
                turn_id=turn_id,
            )
            # Goal 完成判定修复(2026-08-29): total=160 是工具预算上限, 简单任务永不达 → 改为:
            # reason==completed 即 complete(不再依赖 done>=total); 失败/中断 → failed
            try:
                from core.gateway.goal_state import update_goal_status as _ugs_fix
            except Exception:
                _ugs_fix = None
            if reason == "completed" and _g.get("status") in ("active", "paused", "failed"):
                # 2026-09-08 产物缺页守卫: 编号页任务缺 P 页 → 不 complete(防 P8 截断仍完成)
                try:
                    from core.gateway.completion_guard import _artifact_incomplete_pages as _aip_fix

                    _ai_in, _ai_det = _aip_fix(_g.get("user_id") or "", session_id, messages)
                    if _ai_in:
                        print("[ARTIFACT_GUARD] %s %s" % (session_id, _ai_det[:80]))
                        from core.gateway.shared_state import add_steer as _st_ai

                        try:
                            _st_ai(session_id, "[系统] " + _ai_det + "; 请一次性原子补写完整后再报告完成。")
                        except Exception:
                            pass
                        reason = "need_more"
                        _rd_ns = _ai_det
                except Exception as _ai_e:
                    print("[ARTIFACT_GUARD] 校验异常(忽略): %s" % _ai_e)
                # 2026-09-03 假完成防护: completed 但 report 是过渡语(准备/将要做/确认可用等)且无实质产出
                # → 不置 complete, 保持 active(前端可续跑); 仅真正交付(报告/写文件/明确结论)才 complete
                # (qwen2.5vl 测试: Agent 侦察后说"现在确认服务可用性...做准备" 45字符 → 被当完成 → 任务中断)
                # R15(qwen2.5vl 报告任务): report 复读系统阶段提示 2x"[系统] 当前阶段：交付..." → 同样不置 complete
                # 复用第一处已算的 _is_transitional(若 report 传入且为过渡语/系统回声 → 不置 complete)
                if _is_transitional:
                    _why_r15 = "系统回声复读" if _is_sys_echo else "过渡语"
                    print(
                        f"[GOAL_FIX] completed 但 report 为{_why_r15}({len(str(report or ''))}字符), 不置 complete, 保持 active 续跑"
                    )
                else:
                    # S5 完成判定单点: 裁决在 completion_guard.complete_if_valid(过渡语/回声→False),
                    # goal_state.complete_goal 仅作最终执行器; active/paused 正常完成, failed 续跑成功后翻转
                    from core.gateway.completion_guard import complete_if_valid as _cif_s5

                    _cif_s5(_g.get("user_id") or "", session_id, report=report)
                print(f"[GOAL_FIX] completed 置 complete: {_gid[-12:]}")
                # Obsidian 集成: 任务完成 → 写复盘笔记到 vault Reviews/(幂等, 失败不阻塞)
                try:
                    from core.gateway.precision_inject import write_task_review as _wtr

                    _wtr(
                        _g.get("user_id") or "",
                        session_id,
                        str(_gid)[-12:],
                        str(_g.get("objective", "任务"))[:60],
                        str(report or "")[:3000],
                        messages=messages,
                        tool_steps=tool_steps,
                    )
                except Exception:
                    pass
                # 知识迁移(2026-08-30): 任务完成 → 常态自动维护常驻知识
                # (踩坑 → 避坑清单.md; 可复用经验/决策 → 匹配 SOP), 幂等去重
                try:
                    from core.gateway.precision_inject import auto_maintain_knowledge as _amk

                    _amk(str(_g.get("objective", "")), messages=messages, tool_steps=tool_steps)
                except Exception:
                    pass
            elif reason in ("error", "budget_limit") and _g.get("status") == "active":
                # 真失败/预算超限 → failed(不再永久 active 堆积)
                # 注意: max_tokens/paused 是"可续跑"中断(前端自动续跑/continuePausedTask 恢复), 不置 failed
                if _ugs_fix:
                    _ugs_fix(
                        _g.get("user_id") or "", session_id, "failed", note=f"reason={reason} {str(detail or '')[:80]}"
                    )
                    print(f"[GOAL_FIX] {reason} 置 failed: {_gid[-12:]}")
            # total 语义修正(2026-08-29): 无 plan 任务 total=160 是工具预算上限, 非真实目标步数 —
            # completed 时把 total 更新为实际工具数(done), 进度真实化(6/6 而非 6/160)
            try:
                if reason == "completed" and _new_done > 0 and _total > _new_done and _g.get("status") == "complete":
                    from core.gateway.goal_state import update_goal_progress

                    update_goal_progress(_g.get("user_id") or "", session_id, done=_new_done, total=_new_done)
                    _total = _new_done
            except Exception:
                pass
            _goal_info = {
                "goal_id": _gid,
                "progress_delta": {"done": _delta, "total": _total, "pct": int(round(_new_done * 100 / _total))},
            }
    except Exception:
        pass
    try:
        from core.gateway.session_log import EV_TURN_END as _EV_TE
        from core.gateway.session_log import log_event as _log_te

        _log_te(
            session_id,
            _EV_TE,
            {
                "turn_id": turn_id,
                "reason": reason,
                "reason_detail": detail,
                "tools": tools_n,
                "tokens": tokens,
                **_goal_info,
                **({"report": str(report)[:500]} if report else {}),
            },
        )
    except Exception:
        pass
    # Step3 审计接入: turn reason 写入 ledger timeline(前端 /v8/ledger/timeline 面板可见)
    try:
        from core.lib.v8.ledger import ledger

        ledger.record_event(
            server_id=session_id,
            agent_name="V9",
            position="bridge_loop",
            action=f"turn_end:{reason}",
            summary=f"turn_id={turn_id} {detail} tools={tools_n} tokens={tokens}"[:300],
        )
    except Exception:
        pass
    # #8 审计告警主动通知: turn reason=error/blocked/cancelled(含 guard deny 触发的 blocked) → 通知老板
    if reason in ("error", "blocked", "cancelled"):
        try:
            from core.gateway.sandbox_util import notify_boss

            notify_boss(
                event_type="turn_end",
                message=f"V9 任务回合异常: {reason} — {str(detail)[:80]}",
                detail=f"turn_id={turn_id} tools={tools_n} tokens={tokens} session={session_id}",
                level="error" if reason == "error" else "warn",
            )
        except Exception:
            pass
