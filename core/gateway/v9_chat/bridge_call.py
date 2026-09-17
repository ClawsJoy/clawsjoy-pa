# -*- coding: utf-8 -*-
"""P3-B 桥接调用层（从 v9_agent_chat 归位，2026-09-12）。

契约：
1. prepare_request 返回新 messages（不原地改）。
2. make_stream_response 返回生成器；yield 全在本函数内部，不跨函数。
3. run_bridge_async 线程体只写 result_slot（引用传递），不碰模块全局。
4. run_bridge_sync 返回响应 dict，由薄路由 jsonify。
5. _v9_bridge_loop 以 bridge_loop_fn 传入（防循环 import）。
"""
import json
import queue
import threading
import time

from core.gateway.message_assembler import (
    _calc_token_budget,
    _compress_messages,
    _finalize_messages,
    _hard_truncate_messages,
    _tg_estimate,
    _truncate_oversized_messages,
    _validate_messages,
)
from core.gateway.shared_state import _guard_log


def prepare_request(*, messages, tools, model, user_id, session_id):
    """契约：返回新 messages（不原地改）：>50KB 单条截断 + 预算驱动压缩 + TOKEN_GUARD + _finalize_messages。"""
    messages = _truncate_oversized_messages(messages)
    _payload_size = len(json.dumps({"messages": messages, "tools": tools}))
    if _tg_estimate(messages, tools) > _calc_token_budget(model, tools):
        _budget_now = _calc_token_budget(model, tools)
        _est_now = _tg_estimate(messages, tools)
        _n_msgs = max(len(messages), 1)
        _avg_tok = max(_est_now / _n_msgs, 1)
        _target_tok = _budget_now * 0.8
        _keep_dyn = max(min(int(_target_tok / _avg_tok), 20), 4)
        import tiktoken as _tk

        _enc = _tk.encoding_for_model("gpt-4")
        _token_est = sum(len(_enc.encode(str(m))) for m in messages)
        print(
            f"[V9 #41] 请求体 {_payload_size//1024}KB，预估 {_token_est} tokens，预算 {_budget_now}，触发主动压缩 (动态 keep={_keep_dyn}，均 {_avg_tok:.0f} tok/条)"
        )
        # 批191 · #5 补完：统计**不再**在此处单独上报 —— 已收敛到 _compress_messages（压缩唯一出口），
        # 一处上报覆盖「入口 / 每轮 round_start / recovery 截断」三类压缩（此前只有入口这一处 ⇒ 真跑里不亮）。
        messages = _compress_messages(messages, user_id, session_id, keep=_keep_dyn)
        messages = _hard_truncate_messages(messages, _budget_now)
        messages = _validate_messages(messages)
        _est_after = _tg_estimate(messages, tools)
        print(f"[V9 #41] 压缩后: {_est_now} → {_est_after} (budget={_budget_now})")
    _tg_before = _tg_estimate(messages, tools)
    if _tg_before > _calc_token_budget(model, tools) * 0.9:
        _tg_sys = [m for m in messages if m.get("role") == "system"][:2]
        _tg_tail = messages[-4:]
        _tg_summary = {"role": "system", "content": "【上下文摘要】中间消息已被强制截断，保留前 2 条 system 与最近 4 条消息。"}
        messages = _tg_sys + [_tg_summary] + _tg_tail
        if _tg_estimate(messages, tools) > _calc_token_budget(model, tools):
            for _m in messages:
                if _m.get("role") == "system" and len(str(_m.get("content", "") or "")) > 5000:
                    _m["content"] = str(_m["content"])[:5000]
        _guard_log(
            "TOKEN_GUARD", f"[TOKEN_GUARD] 强制截断：{_tg_before} → {_tg_estimate(messages, tools)}", "token_guard.log"
        )
    messages = _finalize_messages(messages)
    return messages


def run_bridge_async(
    *,
    result_slot,
    bridge_loop_fn,
    messages,
    tools,
    user_id,
    session_id,
    adapter,
    thinking2,
    model,
    plan_status,
    current_plan,
    data,
    on_round=None,
):
    """契约：线程体；只写 result_slot["out"]/["err"]，不碰模块全局（sentinel 由调用方放）。"""
    try:
        result_slot["out"] = bridge_loop_fn(
            messages,
            tools,
            user_id,
            session_id,
            adapter,
            thinking2,
            model,
            plan_status,
            current_plan,
            data,
            on_round=on_round,
        )
    except Exception as _e:
        result_slot["err"] = str(_e)
        # ===== 批102：异常必须带 traceback 落盘（体检项 61 的排查侧）=====
        # 事故（批101）：真实轮次崩在 round 0 之后，前端只收到一句
        #   "tuple indices must be integers or slices, not str"，
        #   而**后端日志干干净净**（grep traceback = 0）⇒ 定位不了抛出行，白跑一轮。
        # 与批87/96/97/101 同族：**静默让排查失去抓手**。
        # 本处只加留痕，不改错误处理逻辑。
        try:
            # flush=True 必须加：网关 stdout 是块缓冲，不加则这一行可能长期留在缓冲区里
            #   —— 批102 复跑时补丁已上线却 grep 不到，就是被缓冲吞掉的（静默的又一形态）。
            import sys as _sys
            import traceback as _tb

            print("[BRIDGE_ERROR] %s: %s\n%s" % (type(_e).__name__, _e, _tb.format_exc()), file=_sys.stderr, flush=True)
        except Exception:
            pass


def make_stream_response(
    *,
    bridge_loop_fn,
    messages,
    tools,
    user_id,
    session_id,
    adapter,
    thinking2,
    model,
    plan_status,
    current_plan,
    data,
    max_total_tools,
    goal_info_fn,
):
    """契约：返回生成器；yield 全在本函数内部。内部三段：_stream_on_round / _stream_bridge_worker / _stream_gen。"""
    _evq = queue.Queue(maxsize=200)
    _bridge_result = {}

    def _stream_on_round(rno, steps, thinking):
        try:
            _evq.put_nowait(
                {
                    "type": "progress",
                    "round": rno,
                    "thinking": thinking,
                    "tool_steps": steps,
                    "progress": {
                        "done": len(steps),
                        "total": max_total_tools,
                        "step_index": len(steps),
                        "total_steps": max_total_tools,
                    },
                }
            )
        except Exception:
            pass

    def _stream_bridge_worker():
        try:
            run_bridge_async(
                result_slot=_bridge_result,
                bridge_loop_fn=bridge_loop_fn,
                messages=messages,
                tools=tools,
                user_id=user_id,
                session_id=session_id,
                adapter=adapter,
                thinking2=thinking2,
                model=model,
                plan_status=plan_status,
                current_plan=current_plan,
                data=data,
                on_round=_stream_on_round,
            )
        finally:
            try:
                _evq.put_nowait({"type": "_done_sentinel"})
            except Exception:
                pass

    def _turn_deadline_ms():
        """turn 级硬时限（毫秒）。0/None = 不限。默认 25 分钟。"""
        try:
            from core.gateway.shared_state import _load_v9_execution_policy as _lv9t

            v = ((_lv9t() or {}).get("execution_budget", {}) or {}).get("turn_timeout_ms", 1500000)
            return int(v or 0)
        except Exception:
            return 1500000

    def _request_cancel(session_id):
        try:
            from core.gateway.shared_state import request_cancel as _rc

            _rc(session_id)
            print(f"[CANCEL] turn 收口(request_cancel) session={session_id}")
        except Exception:
            pass

    def _stream_gen():
        # 2026-09-13 修 bug #4 + #7（中断语义统一）：
        #   #4：此前 _evq.get 超时只发心跳、**无限循环** —— 桥接线程一旦挂死，
        #       流会永远心跳下去，前端一直「Thinking」，只能重启网关（实测挂死 10 分钟无日志）。
        #       现在加 turn 级硬时限：超时 → 置取消标志 + 发一条明确的 error 事件 + [DONE]。
        #   #7：此前没有 GeneratorExit 处理 —— 客户端断开后后台线程照跑（实测断开后仍跑 35s），
        #       而在另一条路径下 turn 又会直接中止，四种中断归宿不一致。
        #       现在统一为：**流未正常收尾就关闭 = 取消该 turn**（点停/断开/超时/异常同一归宿）。
        _t0 = time.time()
        _deadline = _turn_deadline_ms()
        _finished = False
        # P0-2(2026-09-13): turn 持久注册表 —— 重启后靠心跳扫描判 STALE，不再「没有终态」。
        _turn_key = None
        try:
            from core.gateway import turn_registry as _tr

            _turn_key = _tr.create_turn(session_id, user_id=user_id)
            try:
                from core.gateway.shared_state import set_continuation as _sc2

                _sc2(session_id, False)  # 新 turn 清续跑哨兵
            except Exception:
                pass
            # 2026-09-13 修：verification_retry 计数必须**每 turn 重置**。
            # 此前 verification_retry_reset 全仓只有定义、生产代码 0 个调用点 →
            # 上限 CAP=2 变成「会话级永久耗尽」：同一会话前 2 次续跑用掉后，
            # 后续所有 turn 都无法再续跑（核验闸门形同失效）。
            try:
                from core.gateway.shared_state import verification_retry_reset as _vrr

                _vrr(session_id)
            except Exception:
                pass
        except Exception as _e_tr:
            print(f"[TURN_REGISTRY] 建 turn 失败(不阻断主流程): {_e_tr}")
        # 批172（PA 前端/系统问题修复）：**流式生成器此前只有 try/finally、没有 except** ⇒
        # 生成器体内一旦抛异常（done 载荷组装 / 核验钩子 / 元组解包等），异常直接逃逸：
        # **既不留 traceback、也不发 error 事件**，前端只能看到一句笼统的 Python 文本
        # （批101/102 亲历 + 2026-09-15 老板再次遇到 ⇒ 同一"留痕缺口"）。
        # 现在：①任何异常都打 [SSE_ERROR] + traceback ②同时发一条**带 run_id/stage**的 error 事件。
        try:
            yield "data: " + json.dumps({"type": "start", "message": "任务开始执行"}, ensure_ascii=False) + "\n\n"
            threading.Thread(target=_stream_bridge_worker, daemon=True).start()
            while True:
                try:
                    _ev = _evq.get(timeout=5)
                except Exception:
                    _elapsed_ms = (time.time() - _t0) * 1000
                    if _deadline and _elapsed_ms > _deadline:
                        _request_cancel(session_id)
                        if _turn_key:
                            try:
                                from core.gateway import turn_registry as _tr3

                                _tr3.finish_turn(_turn_key, "CANCELLED", "turn 超时")
                            except Exception:
                                pass
                        yield "data: " + json.dumps(
                            {
                                "type": "error",
                                "timeout": True,
                                "run_id": (
                                    lambda: __import__(
                                        "core.gateway.run_id", fromlist=["canonical_run_id"]
                                    ).canonical_run_id(session_id)
                                )(),
                                "stage": "turn_timeout",
                                "error": "任务超时（已运行 %.0f 分钟，超过 turn 时限 %d 分钟），已发出取消；"
                                "这不是「没反应」，是系统主动收口。" % (_elapsed_ms / 60000.0, _deadline // 60000),
                            },
                            ensure_ascii=False,
                        ) + "\n\n"
                        yield "data: [DONE]\n\n"
                        _finished = True
                        return
                    if _turn_key:
                        try:
                            from core.gateway import turn_registry as _tr2

                            _tr2.heartbeat_async(_turn_key)
                        except Exception:
                            pass
                    yield "data: " + json.dumps({"type": "heartbeat"}, ensure_ascii=False) + "\n\n"
                    continue
                if _ev.get("type") == "_done_sentinel":
                    break
                yield "data: " + json.dumps(_ev, ensure_ascii=False) + "\n\n"
            _bo = _bridge_result.get("out")
            if _bo is None:
                yield "data: " + json.dumps(
                    {
                        "type": "error",
                        "error": _bridge_result.get("err", "桥接循环异常"),
                        "stage": "bridge_worker",
                        "run_id": (
                            lambda: __import__("core.gateway.run_id", fromlist=["canonical_run_id"]).canonical_run_id(
                                session_id
                            )
                        )(),
                    },
                    ensure_ascii=False,
                ) + "\n\n"
            else:
                _m2, _ts2, _bex2, _fr2, _tk2, _r2, _rd2 = _bo
                if _fr2 is not None:
                    _done_payload = dict(_fr2)
                    if "data" not in _done_payload or not _done_payload.get("data"):
                        _done_payload["data"] = {
                            "choices": [
                                {
                                    "message": {
                                        "role": "assistant",
                                        "content": str(
                                            _done_payload.get("error") or _done_payload.get("message") or "任务执行出错"
                                        ),
                                    }
                                }
                            ]
                        }
                    if "choices" not in (_done_payload.get("data") or {}):
                        _done_payload["data"] = {"choices": [{"message": {"role": "assistant", "content": ""}}]}
                else:
                    _loop_data2 = None
                    for _m_r in reversed(_m2):
                        if _m_r.get("role") == "assistant" and _m_r.get("content"):
                            _loop_data2 = _m_r
                            break
                    if _loop_data2 is None:
                        _loop_data2 = {"role": "assistant", "content": "[系统] 模型未产出有效内容，任务未完成。请重新描述需求或检查环境后重试。"}
                        _empty_reply_flag = True
                    else:
                        _empty_reply_flag = False
                    _done_payload = {
                        "success": True,
                        "data": {"choices": [{"message": _loop_data2}]},
                        "tokens": _tk2,
                        "plan_status": plan_status,
                        "current_plan": current_plan,
                        "tool_steps": _ts2,
                        "progress": {
                            "done": len(_ts2),
                            "total": max_total_tools,
                            "step_index": len(_ts2),
                            "total_steps": max_total_tools,
                        },
                        "bridge_exhausted": _bex2,
                        "goal_info": goal_info_fn(session_id),
                    }
                    if _empty_reply_flag:
                        _done_payload["reason"] = "need_more"
                        _done_payload["reason_detail"] = "模型未产出有效内容，请重试"
                    else:
                        _done_payload["reason"] = _r2
                        _done_payload["reason_detail"] = _rd2
                # 2026-09-13：把核验结论挂到 SSE done payload —— 前端唯一能看到它的通道
                # （前端读不到 session_log；不新增后端能力，verdict 本就在这一步算出来了）。
                try:
                    from core.gateway.v9_bridge.response_guard import _completion_verify as _cvp

                    _bo_p = _bridge_result.get("out")
                    _cvp_res = _cvp(
                        messages=(_bo_p[0] if _bo_p else []) or [],
                        tool_steps=(_bo_p[1] if _bo_p else []) or [],
                        session_id=session_id,
                        user_id=user_id,
                        turn_id=None,
                        lite=True,
                    )
                    _done_payload["verify_verdict"] = _cvp_res.get("verdict")
                    _done_payload["verify_checked"] = _cvp_res.get("checked")
                    _done_payload["verify_failures"] = [str(x)[:200] for x in (_cvp_res.get("failures") or [])[:3]]
                except Exception:
                    _done_payload["verify_verdict"] = None
                _done_payload["type"] = "done"
                try:
                    # 批189 · #5：把本 session 最近一次上下文压缩统计随 done 下发
                    # （前端据此显示「已压缩 N 条」；压缩不是丢弃，是转记忆的第一步可见化）
                    from core.gateway.shared_state import get_last_compact as _glc

                    _done_payload["compact"] = _glc(session_id)
                except Exception:
                    pass
                yield "data: " + json.dumps(_done_payload, ensure_ascii=False) + "\n\n"
            # 2026-09-13 补留痕：核验结果在 stream 收尾统一记录，覆盖所有终态出口。
            # 此前只在 response_guard 的 normal_complete 一条路径上记，plan_pending / 工具上限 /
            # 审批挂起等出口一律不记 → 留痕覆盖率只有 9.8%，任何阈值都无样本可校。
            # 这里只跑轻量版（R6 产物核验，不跑五步链），避免与闸门重复做重活。
            try:
                from core.gateway.session_log import log_event as _le_cov
                from core.gateway.v9_bridge.response_guard import _completion_verify as _cv_lite

                _bo_x = _bridge_result.get("out")
                _msgs_x = (_bo_x[0] if _bo_x else []) or []
                _steps_x = (_bo_x[1] if _bo_x else []) or []
                _cvx = _cv_lite(
                    messages=_msgs_x,
                    tool_steps=_steps_x,
                    session_id=session_id,
                    user_id=user_id,
                    turn_id=None,
                    lite=True,
                )
                _le_cov(
                    session_id,
                    "completion_verify",
                    {
                        "verdict": _cvx.get("verdict"),
                        "passed": _cvx.get("passed"),
                        "checked": _cvx.get("checked"),
                        "stage": "stream",
                        "lite": True,
                        "failures": [str(x)[:200] for x in (_cvx.get("failures") or [])[:5]],
                    },
                )
            except Exception as _e_cov:
                print(f"[COMPLETION_VERIFY] 覆盖率留痕失败(不阻断): {_e_cov}")
            if _turn_key:
                try:
                    from core.gateway import turn_registry as _tr4

                    _tr4.finish_turn(
                        _turn_key, "FAILED" if _bo is None else "COMPLETED", str(_bridge_result.get("err") or "")[:200]
                    )
                except Exception:
                    pass
            yield "data: [DONE]\n\n"
            _finished = True
        except Exception as _e_sse:
            # 批172：异常必须留痕（含 traceback），并把 run_id/stage 交给前端 ⇒ 一句话即可定位。
            try:
                import sys as _sys_sse
                import traceback as _tb_sse

                _rid_sse = "?"
                try:
                    from core.gateway.run_id import canonical_run_id as _cr_sse

                    _rid_sse = _cr_sse(session_id)
                except Exception:
                    pass
                print(
                    "[SSE_ERROR] 流式生成器异常 run_id=%s session=%s: %s: %s\n%s"
                    % (_rid_sse, session_id, type(_e_sse).__name__, _e_sse, _tb_sse.format_exc()),
                    file=_sys_sse.stderr,
                    flush=True,
                )
                yield "data: " + json.dumps(
                    {"type": "error", "error": str(_e_sse)[:300], "run_id": _rid_sse, "stage": "sse_generator"},
                    ensure_ascii=False,
                ) + "\n\n"
                yield "data: [DONE]\n\n"
                _finished = True
            except Exception:
                pass
        finally:
            # 走到这里而 _finished 仍为 False ⇒ 生成器被提前关闭（客户端断开/异常/中途 return）
            # ⇒ 统一语义：取消该 turn。后台线程会在下一个检查点退出。
            if not _finished:
                # P0-2: 断开不是「没有终态」—— 落一条 DETACHED，重启扫描时能认出来。
                if _turn_key:
                    try:
                        from core.gateway import turn_registry as _tr5

                        _tr5.detach_turn(_turn_key, "客户端断开/流提前关闭")
                    except Exception:
                        pass
                _request_cancel(session_id)

    return _stream_gen()


def run_bridge_sync(
    *,
    bridge_loop_fn,
    messages,
    tools,
    user_id,
    session_id,
    adapter,
    thinking2,
    model,
    plan_status,
    current_plan,
    data,
    max_total_tools,
    goal_info_fn,
):
    """契约：返回响应 dict（final_resp 优先，否则组装正常响应）；由薄路由 jsonify。"""
    _loop_out = bridge_loop_fn(
        messages, tools, user_id, session_id, adapter, thinking2, model, plan_status, current_plan, data
    )
    messages, _tool_steps, _bridge_exhausted, _final_resp, tokens, _r_ns, _rd_ns = _loop_out
    if _final_resp is not None:
        return _final_resp
    _loop_data = None
    for _m_r in reversed(messages):
        if _m_r.get("role") == "assistant" and _m_r.get("content"):
            _loop_data = _m_r
            break
    if _loop_data is None:
        _loop_data = {"role": "assistant", "content": "[系统] 模型未产出有效内容，任务未完成。请重新描述需求或检查环境后重试。"}
        _empty_reply_flag_ns = True
    else:
        _empty_reply_flag_ns = False
    _resp_ns = {
        "success": True,
        "data": {"choices": [{"message": _loop_data}]},
        "tokens": tokens,
        "plan_status": plan_status,
        "current_plan": current_plan,
        "tool_steps": _tool_steps,
        "progress": {
            "done": len(_tool_steps),
            "total": max_total_tools,
            "step_index": len(_tool_steps),
            "total_steps": max_total_tools,
        },
        "bridge_exhausted": _bridge_exhausted,
        "goal_info": goal_info_fn(session_id),
    }
    if _empty_reply_flag_ns:
        _resp_ns["reason"] = "need_more"
        _resp_ns["reason_detail"] = "模型未产出有效内容，请重试"
    else:
        _resp_ns["reason"] = _r_ns
        _resp_ns["reason_detail"] = _rd_ns
    return _resp_ns
