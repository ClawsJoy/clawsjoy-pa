# -*- coding: utf-8 -*-
"""S6-C 响应守卫：预算收敛 + 响应归一化（从 _v9_bridge_loop 归位，2026-09-12）。"""

import time  # 批186 · D3：plan_pending 分支用到 time.time()，此前模块内**无** import ⇒ NameError 被自身 except 吞成「检测异常(忽略)」⇒ 计划等待确认被当成 normal_complete（假完成）。变更前现场：`[PLAN_WAIT] 计划等待检测异常(忽略): name 'time' is not defined`


def _budget_limit_guard(
    *,
    tokens,
    messages,
    adapter,
    user_id,
    session_id,
    tool_steps,
    turn_id,
    bridge_exhausted,
    progress_fn,
    goal_info_fn,
    write_turn_end_fn,
):
    """S6-C 预算收敛守卫：单任务 token 超预算 → 无工具收尾总结并返回最终响应。

    契约：返回 final_resp（超预算）或 None（未超）。原地改 messages（append 收尾指令）。
    """
    try:
        from core.gateway.shared_state import _load_v9_execution_policy as _l9p

        _budget_tok = int(
            ((_l9p() or {}).get("execution_budget", {}) or {}).get("per_task_token_budget", 500000) or 500000
        )
    except Exception:
        _budget_tok = 500000
    if tokens > _budget_tok:
        # R1(2026-08-30 架构根治): budget_limit 改为正常收尾(不是失败) — 注入总结指令,
        # 让 LLM 基于已完成操作直接总结输出; goal 保持可续跑(max_tokens 语义), 不置 failed。
        # 原 success=False 前端显示"失败", 实际任务可能已完成大半 → 伪失败重复计费。
        # 2026-09-07 修复: 原「伪造 assistant 总结模板」直接当最终输出, LLM 从未参与 →
        # 「已完成:/未完成:」永远为空(红果漫剧任务 50 万 token 截断后空总结实证)。
        # 改为: 追加 system 收尾指令后, 跑一次「无工具」LLM 收尾轮(小 max_tokens, 关 thinking),
        # 让模型基于本轮已获取内容产出真实交付总结(含未落盘目标与下一步)。
        print(f"[COST_GUARD] 单任务 tokens {tokens} 超预算 {_budget_tok}, 无工具收尾总结")
        _bmsg_guard = {
            "role": "system",
            "content": (
                "⚠️ 工具预算已耗尽(累计 %d tokens ≥ 预算 %d), 工具执行停止, 禁止再调用任何工具。"
                "请立即输出最终交付总结:"
                "1) 本任务实际已完成/已获取到的内容(如实引用你上方已读到的材料);"
                "2) 尚未完成的部分——若任务要求落盘(write_note/write_draft/write_file)但尚未写入, 说明目标路径与内容要点;"
                "3) 结束语注明: 回复「继续」可完成剩余落盘。"
                "（B 块 2026-09-13: 此刻任务原文与可续跑上下文已落盘到 .agent_state.json/BRIEF.md, "
                "「继续」会带上任务原文续跑, 不会丢上下文——此前该轮不落盘, 回复「继续」直接 no_context。）"
            )
            % (tokens, _budget_tok),
        }
        messages.append(_bmsg_guard)
        _final_txt = ""
        try:
            _fin_r = adapter.execute_with_tools(
                messages=messages, tools=[], user_id=user_id, temperature=0.3, max_tokens=3000, thinking=False
            )
            if _fin_r and _fin_r.get("success"):
                _final_txt = str(
                    ((_fin_r.get("data") or {}).get("choices") or [{}])[0].get("message", {}).get("content") or ""
                )
        except Exception as _fin_e:
            print(f"[COST_GUARD] 收尾总结调用失败: {_fin_e}")
        if not str(_final_txt).strip():
            _final_txt = "⚠️ 预算不足，任务未完全完成。请回复「继续」以在下一轮完成剩余写入" "（任务原文与可续跑上下文已落盘，续跑不会丢上下文）。" + (
                f"\n(本任务已执行 {len(tool_steps)} 个工具步骤, 关键内容见上方工具结果。)" if tool_steps else ""
            )
        _bmsg_guard = {"role": "assistant", "content": _final_txt}
        write_turn_end_fn(
            session_id, turn_id, tokens, "max_tokens", f"单任务 token 达预算({tokens}>={_budget_tok})，已正常收尾", len(tool_steps)
        )
        return (
            messages,
            tool_steps,
            bridge_exhausted,
            {
                "success": True,
                "status": "token_water",
                "data": {"choices": [{"message": _bmsg_guard}]},
                "reason": "token_water",
                "reason_detail": f"单任务 token 达预算({tokens}>={_budget_tok})，已正常收尾",
                "tokens": tokens,
                "compact": __import__("core.gateway.shared_state", fromlist=["get_last_compact"]).get_last_compact(
                    session_id
                ),
                "progress": progress_fn(),
                "goal_info": goal_info_fn(session_id),
            },
            tokens,
            None,
            None,
        )
    return None


def _completion_verify(*, messages, tool_steps, session_id, user_id, turn_id, lite=False, expected_min_bytes=None):
    """通用完成核验闸门（2026-09-13）：把「早就造好但没接线」的 verifier 接到完成分支上。

    机制（三层，全部是既有资产）：
      1. `core/pa/artifact.py verify_artifacts`（R6）—— 拦占位产物（68 字节 stub / 过小文件）；
      2. `core/lib/verification_chain.py run_verification_chain` —— 五步链（写入→语法→运行→内容→done_when）；
      3. `core/gateway/audit.py cross_check_completion` —— 声称 vs 审计记录交叉复核。

    契约：返回 {"passed": bool, "failures": [str], "checked": bool}。
    **只在「本 turn 出现过真写工具（write_file/write_large/edit_file）的成功」时才核验** ——
    纯问答、只读任务、vault 写（obsidian_knowledge）不拦（不退化）。
    任何异常 → passed=True（宁可不拦，不可误伤）。env V9_COMPLETION_VERIFY=0 可整体关停。
    """
    try:
        import os as _os_cv

        if str(_os_cv.environ.get("V9_COMPLETION_VERIFY", "1")) == "0":
            return {"passed": True, "failures": [], "checked": False, "verdict": "NOT_APPLICABLE"}
        _wt = ("write_file", "write_large", "edit_file")
        _wrote = [s for s in (tool_steps or []) if str(s.get("tool") or "") in _wt and s.get("success")]
        _evidence = "tool_step"
        if not _wrote:
            # 批188 · 缺陷2（假失败）：审批后补执行的成功写**不在本 turn 的 tool_steps 里**
            # （approval.py::_handle_write_approval 直接执行，不 append tool_step）
            # ⇒ 用「本 session 近 30 分钟已批准的文件」当**线索**去核产物；
            # 真伪仍由 verify_artifacts 判定（不存在/过小/占位仍会 FAIL）——不制造假绿。
            try:
                from core.gateway.shared_state import approved_files as _af_ap

                _ap_paths = [
                    p for p in (_af_ap(session_id, within_s=1800) or []) if p and not str(p).startswith("cmd:")
                ]
            except Exception:
                _ap_paths = []
            if _ap_paths:
                _wrote = [
                    {"tool": "write_file", "arg": p, "success": True, "source": "approved_write"} for p in _ap_paths
                ]
                _evidence = "approved_write"
        if not _wrote:
            return {"passed": True, "failures": [], "checked": False, "verdict": "NOT_APPLICABLE", "evidence": "none"}
        failures = []
        chain_ran = False
        chain_skip_reason = ""
        # 路径基准 = **会话沙箱**, 不是网关 cwd。
        # 实测事故: 按 cwd 解析 → 文件明明写在沙箱里却判「产物不存在」→ 误拦合法完成
        # 并触发无意义续跑(live 实证: data/reports/_verify_probe.md 实际已写入)。
        _base = None
        try:
            from core.lib.gateway_helpers import _get_sandbox_base as _gsb_cv

            _base = _gsb_cv(user_id, session_id)
        except Exception as _e_base:
            print(f"[COMPLETION_VERIFY] 取沙箱基准失败(退回 cwd): {_e_base}")
        # R6：逐个产物做占位核验
        try:
            from core.pa.artifact import verify_artifacts as _va

            _paths = [str(s.get("arg") or "").strip() for s in _wrote]
            _paths = [p for p in _paths if p]
            if _paths:
                _av = _va(_paths, base_dir=_base, expected_min_bytes=expected_min_bytes)
                if not _av.get("ok"):
                    failures.extend(_av.get("failures") or [])
        except Exception as _e_r6:
            print(f"[COMPLETION_VERIFY] R6 产物核验异常(跳过): {_e_r6}")
        if lite:
            # 轻量版（覆盖率留痕用）：只做 R6 产物核验，不跑五步链/审计复核（那些有开销）
            return {
                "passed": not failures,
                "failures": failures,
                "checked": True,
                "verdict": "PASS" if not failures else "FAIL",
                "evidence": _evidence,
                "chain_ran": False,
            }
        # 五步链 + 审计交叉复核
        _vc = {}
        try:
            # base_dir 契约 = 沙箱的**父目录**（project_root 再拼沙箱目录名）。
            # 此前直接传沙箱本身 → 路径双拼 .../clawsjoy_dev/clawsjoy_dev → 异常被吞 → 五步链从未跑成。
            from pathlib import Path as _P_cv

            from core.lib.verification_chain import run_verification_chain as _rvc

            _bd_cv = _P_cv(_base) if _base else None
            if _bd_cv is not None and _bd_cv.name == "clawsjoy_dev":
                _bd_cv = _bd_cv.parent
            _vc = (
                _rvc(
                    task_name=session_id,
                    session_id=session_id,
                    user_id=user_id,
                    messages=messages,
                    task_goal="",
                    require_write=True,
                    base_dir=_bd_cv,
                )
                or {}
            )
            chain_ran = bool(_vc.get("steps"))
            # 2026-09-13：链 verdict 进事件流（此前只落 data/verification_reports/*.json，
            # 可观测性下降 —— 覆盖率初衷是「可查、可断言」，链的结果也必须可查）。
            try:
                from core.gateway.session_log import log_event as _le_chain

                _le_chain(
                    session_id,
                    "completion_verify",
                    {
                        "verdict": "PASS" if _vc.get("passed") else "FAIL",
                        "stage": "chain",
                        "lite": False,
                        "chain_ran": chain_ran,
                        "steps": list((_vc.get("steps") or {}).keys()),
                        "failures": [str(x)[:200] for x in ((_vc.get("failures") or [])[:5])],
                    },
                    turn_id=turn_id,
                    step_id=0,
                )
            except Exception as _e_lc:
                print(f"[COMPLETION_VERIFY] 链 verdict 落盘失败(不阻断): {_e_lc}")
            # Capability Ledger：verification 的存活记录（SKIPPED 在这里现形）
            try:
                from core.gateway import capability_ledger as _cl

                _cl.record(
                    "verification",
                    session_id,
                    "PASS" if _vc.get("passed") else "FAIL",
                    expected=True,
                    turn_id=turn_id,
                    detail="chain_ran=%s files=%d" % (chain_ran, len(_wrote)),
                )
            except Exception:
                pass
            if not _vc.get("passed"):
                # 证据源冲突裁决：五步链从 messages 里猜「有没有写入」，而 tool_steps 是每轮的
                # 权威记录（我们已经用它判定本 turn 确实写成功）。两者冲突时以 tool_steps 为准，
                # 否则会把合法完成误判成假完成 → 无意义续跑烧 token（fault 测试暴露的误伤路径）。
                _WRITE_MISS = "未检测到任何 write_file"
                for _f in _vc.get("failures") or []:
                    if _WRITE_MISS in str(_f):
                        print("[COMPLETION_VERIFY] 五步链判无写入，但 tool_steps 有成功写入 → 以 tool_steps 为准，不判失败")
                        continue
                    failures.append(_f)
        except Exception as _e_vc:
            # 不静默：跳过必须显式标出来，调用方/测试才能断言「没被跳过」
            chain_ran = False
            chain_skip_reason = str(_e_vc)[:200]
            print(f"[COMPLETION_VERIFY][CHAIN_SKIPPED] 五步链异常(跳过): {_e_vc}")
            try:
                from core.gateway.session_log import log_event as _le_skip

                _le_skip(
                    session_id,
                    "completion_verify_skip",
                    {"stage": "chain", "reason": chain_skip_reason},
                    turn_id=turn_id,
                    step_id=0,
                )
            except Exception:
                pass
            # Capability Ledger：跳过也必须留痕（SKIPPED 是这张表存在的理由）
            try:
                from core.gateway import capability_ledger as _cl2

                _cl2.record(
                    "verification",
                    session_id,
                    "SKIPPED",
                    expected=True,
                    turn_id=turn_id,
                    detail="chain_skip: %s" % chain_skip_reason,
                )
            except Exception:
                pass
        try:
            from core.gateway.audit import cross_check_completion as _ccc

            _cc = _ccc(_vc, session_id, user_id=user_id) or {}
            if not _cc.get("audit_passed", True):
                failures.extend(_cc.get("audit_failures") or [])
        except Exception as _e_cc:
            print(f"[COMPLETION_VERIFY] 审计复核异常(跳过): {_e_cc}")
        if failures:
            print("[COMPLETION_VERIFY] 未通过，回灌续跑：%s" % " | ".join(str(x)[:120] for x in failures[:3]))
        return {
            "passed": not failures,
            "failures": failures,
            "checked": True,
            "verdict": "PASS" if not failures else "FAIL",
            "evidence": _evidence,
            "chain_ran": chain_ran,
            "chain_skip_reason": chain_skip_reason,
        }
    except Exception as _ce:
        print(f"[COMPLETION_VERIFY] 核验整体异常(跳过, 不拦): {_ce}")
        return {"passed": True, "failures": [], "checked": False, "verdict": "NOT_APPLICABLE"}


def _normalize_bridge_response(*, data_resp, session_id):
    """S6-C 响应归一化：取 message/tool_calls + maxSteps 硬截断。返回 (bmsg, btool_calls)。"""
    bmsg = data_resp["choices"][0].get("message", {})
    btool_calls = bmsg.get("tool_calls") or []
    # #6 maxSteps 硬限制: 每轮工具数上限(execution_policy.yaml max_tools_per_round, 默认 12), 超限截断+注入收敛提示
    try:
        from core.gateway.shared_state import _load_v9_execution_policy

        _max_tpr = int(
            ((_load_v9_execution_policy() or {}).get("execution_budget", {}) or {}).get("max_tools_per_round", 12) or 12
        )
    except Exception:
        _max_tpr = 12
    if len(btool_calls) > _max_tpr:
        bmsg["content"] = (bmsg.get("content") or "") + (
            f"\n\n[系统] 本轮工具调用数 {len(btool_calls)} 超上限 {_max_tpr}，已截断为前 {_max_tpr} 个。请收敛操作，优先完成关键写入。"
            if bmsg.get("content")
            else ""
        )
        btool_calls = btool_calls[:_max_tpr]
    return bmsg, btool_calls


def _run_response_guard(
    *,
    messages,
    data_resp,
    bmsg,
    btool_calls,
    session_id,
    bridge_round,
    turn_id,
    tokens,
    tool_steps,
    bridge_exhausted,
    empty_reply_count,
    no_think,
    detect_ask_fn,
    is_plan_message_fn,
    ctx_summary_fn,
    write_turn_end_fn,
    ts_progress_fn,
    goal_info_fn,
    plan_pending,
    user_id="",
):
    """S6-C 残段响应守卫：ask 提问 / plan_pending / 空回复重试 / 正常完成。

    契约：原地改 messages；返回决策 dict {final_resp, empty_retry, normal_complete, empty_reply_count, no_think}。
    final_resp 非 None 时调用方 return；empty_retry 时 continue；normal_complete 时 break。
    """
    # #101 G3 ask 式提问通道（H1 提取: 检测逻辑独立）
    _ask_result = detect_ask_fn(bmsg)
    if _ask_result is not None:
        _ask_text = _ask_result["question"]
        print(f"[ASK_GATE] Agent 提问: {_ask_text[:80]} / {len(_ask_result['options'])} 选项")
        write_turn_end_fn(session_id, turn_id, tokens, "ask", _ask_text[:200], len(tool_steps))
        # 批175 修复（主指标·假失败）：这里此前返回的是**桥接循环的 7 元组**（S6-C 归位前的旧契约残留），
        # 而本函数已改为返回**决策 dict**（见本函数 docstring），调用方 agent_gateway_enhanced.py:549
        # 按 dict 取 `_resp["final_resp"]` ⇒ TypeError: tuple indices must be integers or slices, not str
        # ⇒ 桥接线程崩 ⇒ SSE 发 error(stage=bridge_worker) ⇒ PA 页把「正常请示」显示成「已失败」= 假失败。
        # 证据：探针 run_id=pa175_ask_probe:1（同一 run 内 turn_end reason=ask 与 error 事件同现）；
        # 进程内复现：ask 分支返回 tuple，调用方取键即抛该 TypeError（批101 起悬案首次捕获）。
        return {
            "final_resp": {
                "success": True,
                "status": "ask",
                "data": data_resp,
                "ask": _ask_result,
                "tool_steps": tool_steps,
                "progress": ts_progress_fn(),
                "tokens": tokens,
                "compact": __import__("core.gateway.shared_state", fromlist=["get_last_compact"]).get_last_compact(
                    session_id
                ),
                "reason": "ask",
                "reason_detail": _ask_text[:200],
                "goal_info": goal_info_fn(session_id),
            },
            "empty_retry": False,
            "normal_complete": False,
            "empty_reply_count": empty_reply_count,
            "no_think": no_think,
        }
    # 2026-09-06 修复: agent 输出「计划等待确认」却无工具调用 → 返回 plan_pending(blocked),
    # 不当作正常完成收尾(否则 UI 显示 ✅完成 但无实际写入 = 假完成)。
    # 触发条件: 系统曾注入确认式规划指令([系统指令]...请先列出修改计划，询问用户确认后再执行)
    # 且本轮 agent 输出是计划文本(_is_plan_message: 步骤结构+无✅/已完成) → 停在等老板确认。
    if not btool_calls and bmsg.get("content"):
        try:
            _sys_injected_confirm = any(
                "询问用户确认后再执行" in str(_m.get("content") or "") for _m in messages if _m.get("role") == "system"
            ) or any("询问用户确认后再执行" in str(_m.get("content") or "") for _m in messages if _m.get("role") == "user")
            _is_plan_only = is_plan_message_fn(str(bmsg.get("content") or ""))
            if _sys_injected_confirm and _is_plan_only:
                print("[PLAN_WAIT] Agent 列出计划等待确认(无写入) → plan_pending, 非完成")
                write_turn_end_fn(session_id, turn_id, tokens, "plan_pending", "Agent 已列计划等待确认(无实际写入)", len(tool_steps))
                messages.append({"role": "assistant", "content": str(bmsg.get("content") or "")})
                _pp_info = {
                    "plan": str(bmsg.get("content") or "")[:2000],
                    "intents": 3,
                    "approved": False,
                    "ts": time.time(),
                    "session_id": session_id,
                }
                plan_pending[session_id] = _pp_info
                # 批175：同类同因（与上方 ask 分支同一个契约缺陷）——此前返回桥接循环的 7 元组，
                # 调用方按决策 dict 取键 ⇒ 同样抛 TypeError ⇒ 「计划等待确认」也会显示成「已失败」。
                # 同一改动单元内一并修正，避免留下同型号的第二枚地雷。
                return {
                    "final_resp": {
                        "success": True,
                        "status": "plan_pending",
                        "data": data_resp,
                        "plan_pending_info": _pp_info,
                        "tool_steps": tool_steps,
                        "progress": ts_progress_fn(),
                        "tokens": tokens,
                        "compact": __import__(
                            "core.gateway.shared_state", fromlist=["get_last_compact"]
                        ).get_last_compact(session_id),
                        "reason": "blocked",
                        "reason_detail": "计划等待老板确认",
                        "goal_info": goal_info_fn(session_id),
                    },
                    "empty_retry": False,
                    "normal_complete": False,
                    "empty_reply_count": empty_reply_count,
                    "no_think": no_think,
                }
        except Exception as _plw_e:
            print(f"[PLAN_WAIT] 计划等待检测异常(忽略): {_plw_e}")
    if not btool_calls:
        # P0 + (a)2026-09-05: 首轮空回复 — 注入「上一轮上下文摘要」自动重试 1 次;
        # 重试仍空 → 走下方 break → need_more(消除瞬态空回复中断, 不再盲目 2 次通用提示)
        if not bmsg.get("content") and empty_reply_count < 1:
            empty_reply_count += 1
            no_think = True  # (2026-09-05) 空回复重试强制关 thinking: reasoning-only 残留时让模型直接产出
            print("[NO_THINK] 空回复重试: 关闭 thinking")
            _empt_summ = ctx_summary_fn(messages)
            print(f"[V9_EMPTY] 首轮空回复({empty_reply_count}/1), 注入上下文摘要重试")
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "[系统] 你上一条回复为空。上一轮进展摘要："
                        + (_empt_summ or "（无，任务刚开始）")
                        + "。请直接基于该摘要继续输出实质内容或调用工具推进任务，不要回复空内容、不要复读提示。"
                    ),
                }
            )
            return {
                "final_resp": None,
                "empty_retry": True,
                "normal_complete": False,
                "empty_reply_count": empty_reply_count,
                "no_think": no_think,
            }
        # 基准修复: 正常完成(有内容) — 最终回复落 messages + 事件日志,
        # 否则 stream done 扫描 messages 找不到最终 assistant → 误判 need_more(空回复)
        if bmsg.get("content"):
            messages.append({"role": "assistant", "content": bmsg.get("content", "")})
            if bmsg.get("reasoning_content"):
                messages[-1]["reasoning_content"] = bmsg["reasoning_content"]
            try:
                from core.gateway.session_log import log_event as _log_final

                _log_final(
                    session_id,
                    "assistant_message",
                    {
                        "content": bmsg.get("content", ""),
                        "reasoning_content": bmsg.get("reasoning_content")
                        if isinstance(bmsg.get("reasoning_content"), str)
                        else "",
                    },
                    turn_id=bridge_round,
                    step_id=0,
                )
            except Exception:
                pass
        # ===== 2026-09-13 完成核验闸门（接 verifier）=====
        # 「模型说完了」只是触发信号；是否允许落 completed 由 verifier 判定（completion 是派生字段）。
        # 未过 → 不落 completed，把 failures 回灌 messages 让 agent 续跑（最多 2 次，防卡死）。
        if bmsg.get("content"):
            # 任务级期望值优先（上游接线，2026-09-13）：从 goal objective 里解析**显式**规格。
            # 无显式规格 → None → 交类型注册表判定（不猜，避免制造新的误判源）。
            _exp_mb = None
            try:
                _gi = goal_info_fn(session_id) or {}
                from core.pa.artifact import parse_expected_min_bytes as _pemb

                _exp_mb = _pemb(_gi.get("objective") or _gi.get("goal_objective") or "")
            except Exception:
                _exp_mb = None
            _cv = _completion_verify(
                messages=messages,
                tool_steps=tool_steps,
                session_id=session_id,
                user_id=user_id,
                turn_id=turn_id,
                expected_min_bytes=_exp_mb,
            )
            # P0-1(2026-09-13): 完成与否由 verifier 的 verdict 派生，不再由「有 content」决定。
            #   PASS / NOT_APPLICABLE -> 干净完成；FAIL -> 未核验完成。
            #   是否**强制**拦住仍由 BLOCK 开关控制（默认 0 只报不拦，见下方注释）。
            _verdict = _cv.get("verdict") or (
                "NOT_APPLICABLE" if not _cv.get("checked") else ("PASS" if _cv.get("passed") else "FAIL")
            )
            if _verdict == "FAIL":
                _allow_retry = False
                try:
                    from core.gateway.shared_state import verification_retry_bump as _vrb

                    _allow_retry = bool(_vrb(session_id))
                    _vrb_count = 0
                    try:
                        from core.gateway.shared_state import _verification_retry as _vr_map

                        _vrb_count = int((_vr_map or {}).get(session_id, 0)) or 1
                    except Exception:
                        _vrb_count = 1
                except Exception:
                    _allow_retry = False
                # 2026-09-13 live 实证：续跑(verification_retry → continue)会撞 400
                # 「reasoning_content must be passed back」—— 连续两次实测复现，且历史会话 0 次出现，
                # 判定为本次接线引入的路径问题（根因待查）。按「不退化优先」：
                # **默认只报不拦**（记录 + 留痕 + 打印），确认续跑路径安全后再用
                # V9_COMPLETION_VERIFY_BLOCK=1 打开拦截。
                import os as _os_blk

                # 2026-09-13 live 实证：400 已修（注入消息按 source=runtime_context 落盘，2 次续跑 0 次 400），
                # 但**开拦截的代价不可接受** —— 512 字节阈值对「按指令写的极小文件」是误判，
                # 而续跑会把误判放大：实测单任务 14 次工具 / 140,483 tokens、4 个垃圾产物、
                # 并往 Obsidian 塞 2 条 pitfall + 1 篇修复报告。
                # 结论：先用「只报不拦」跑一段收集 verdict 分布（含按产物类型校准阈值），再开拦截。
                _blocking = str(_os_blk.environ.get("V9_COMPLETION_VERIFY_BLOCK", "0")) == "1"
                if _allow_retry and _blocking:
                    _fails = [str(x) for x in (_cv.get("failures") or [])][:5]
                    _cv_msg = "[系统] 完成核验未通过，请修正后继续（不要只是复述已完成）：\n- " + "\n- ".join(_fails)
                    # 2026-09-13：记录续跑代价（**只记录不拦** —— 先拿真实分布再定 retry_token_cap）
                    try:
                        from core.gateway import capability_ledger as _cl_cc

                        _cl_cc.record_continuation_cost(
                            session_id,
                            attempt=(_vrb_count or 1),
                            tokens_total=tokens,
                            tools_total=len(tool_steps or []),
                            verdict=_verdict,
                            failures_n=len((_cv.get("failures") or [])),
                            turn_id=turn_id,
                        )
                    except Exception:
                        pass
                    messages.append({"role": "user", "content": _cv_msg})
                    # 续跑哨兵置位：续跑期间禁写 vault（统一守卫在 tool_runner._run_item 裁决）
                    try:
                        from core.gateway.shared_state import set_continuation as _sc

                        _sc(session_id, True)
                    except Exception:
                        pass
                    # 2026-09-13 修 400：注入消息必须落盘（source=runtime_context）。
                    # 系统约定见 loop.py:114 / execute_agent_task.py:979；否则下一轮 rebuild_context
                    # → derive_messages 重建时它被丢掉 → 续跑变成「拿同一份上下文再调一次」且 messages
                    # 以 assistant 收尾 → DeepSeek 400 reasoning_content must be passed back
                    # （live 连续两次复现，历史会话 0 次出现）。
                    try:
                        from core.gateway.session_log import log_event as _le_cv2

                        _le_cv2(
                            session_id,
                            "user_message",
                            {"role": "user", "content": _cv_msg, "source": "runtime_context"},
                            turn_id=bridge_round,
                            step_id=0,
                        )
                    except Exception as _e_lg:
                        print(f"[COMPLETION_VERIFY] 续跑消息落盘失败(可能仍会 400): {_e_lg}")
                    return {
                        "final_resp": None,
                        "empty_retry": False,
                        "normal_complete": False,
                        "verification_retry": True,
                        "empty_reply_count": empty_reply_count,
                        "no_think": no_think,
                    }
                elif _allow_retry and not _blocking:
                    print(
                        "[COMPLETION_VERIFY] 只报不拦（V9_COMPLETION_VERIFY_BLOCK 未开）：%s"
                        % " | ".join(str(x)[:120] for x in (_cv.get("failures") or [])[:3])
                    )
                else:
                    print("[COMPLETION_VERIFY] 重试已达上限，按正常完成收尾（不再拦，防卡死）")
        bridge_exhausted = False  # #103 O1：正常结束（未跑满）
        return {
            "final_resp": None,
            "empty_retry": False,
            "normal_complete": True,
            "empty_reply_count": empty_reply_count,
            "no_think": no_think,
            "verify_verdict": locals().get("_verdict", "NOT_APPLICABLE"),
        }
    return {
        "final_resp": None,
        "empty_retry": False,
        "normal_complete": False,
        "empty_reply_count": empty_reply_count,
        "no_think": no_think,
    }
