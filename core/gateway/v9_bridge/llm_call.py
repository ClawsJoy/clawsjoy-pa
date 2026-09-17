# -*- coding: utf-8 -*-
"""S6-B LLM 调用 + 7B 降级（从 _v9_bridge_loop 归位，2026-09-12）。"""


def call_bridge_llm(
    *,
    messages,
    tools,
    user_id,
    session_id,
    adapter,
    mt_out,
    thinking2,
    no_think,
    bridge_round,
    is_7b_fallback,
    daily_cost_exceeded,
    last_7b_result,
    data,
):
    """S6-B LLM 调用：7B 降级 + 只读收敛注入 + execute_with_tools + 402 降级重试。

    契约：原地改 messages（只读收敛 append）；返回 (resp, is_7b_fallback)。
    daily_cost_exceeded / last_7b_result 由调用方从 main globals 读取传入（状态解耦）。
    """
    from core.gateway.shared_state import _session_write_tracker

    # P0 费用保护: 每日费用超限 → 直接走 7B(不再调 DeepSeek)
    if daily_cost_exceeded:
        print("[COST_GUARD] 今日费用超限, 本轮直接走 7B")
        is_7b_fallback = True
        try:
            from core.lib.llm_client import llm_client

            _tools_hint = (
                "可用工具："
                + chr(10)
                + chr(10).join(
                    [
                        f"- {t.get('function',{}).get('name','')}: {t.get('function',{}).get('description','')[:100]}"
                        for t in tools
                        if isinstance(t, dict) and t.get("function")
                    ]
                )
            )
            _user_prompt = str(data.get("message", "") if isinstance(data, dict) else "") or ""
            if not _user_prompt and isinstance(data, dict):
                for _m_d in reversed(data.get("messages", []) or []):
                    if isinstance(_m_d, dict) and _m_d.get("role") == "user" and _m_d.get("content"):
                        _user_prompt = str(_m_d.get("content", ""))
                        break
            if not _user_prompt:
                for _m_rev in reversed(messages):
                    if _m_rev.get("role") == "user" and _m_rev.get("content"):
                        _user_prompt = str(_m_rev.get("content", ""))
                        break
            _system_prompt = "你是 ClawsJoy 的执行助手，调用工具完成用户任务。今日 DeepSeek 费用已超限，本任务由本地模型执行。"
            _chat_msgs = [{"role": "system", "content": _system_prompt}, {"role": "user", "content": _user_prompt}]
            _last_tc = last_7b_result
            if _last_tc:
                _chat_msgs.append({"role": "tool", "content": str(_last_tc)[:1500]})
                _chat_msgs.append({"role": "user", "content": "如果上面的工具结果已满足需求，请直接输出中文报告，不要再次调用工具。"})
            import requests as _req7b_dl

            _r7b = _req7b_dl.post(
                "http://127.0.0.1:11434/api/chat",
                json={
                    "model": "qwen2.5:7b-instruct-q4_0-gpu",
                    "messages": _chat_msgs,
                    "tools": tools,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 512},
                },
                timeout=(30, 120),
            )
            _r7b_json = _r7b.json() if _r7b.status_code == 200 else {}
            _ollama_msg = _r7b_json.get("message", {}) or {}
            _ollama_txt = str(_ollama_msg.get("content", "") or "")
            _ollama_tcs = _ollama_msg.get("tool_calls") or []
            if _ollama_tcs:
                _tc0 = _ollama_tcs[0].get("function", {}) or {}
                _tcn = str(_tc0.get("name", "")).strip()
                if _tcn:
                    resp = {
                        "success": True,
                        "data": {
                            "choices": [
                                {
                                    "message": {
                                        "role": "assistant",
                                        "content": "",
                                        "tool_calls": [
                                            {
                                                "id": "call_7b",
                                                "type": "function",
                                                "function": {"name": _tcn, "arguments": _tc0.get("arguments", {})},
                                            }
                                        ],
                                    }
                                }
                            ]
                        },
                        "tokens": 0,
                    }
                else:
                    resp = {
                        "success": True,
                        "data": {"choices": [{"message": {"role": "assistant", "content": _ollama_txt}}]},
                        "tokens": 0,
                    }
            else:
                resp = {
                    "success": True,
                    "data": {
                        "choices": [
                            {"message": {"role": "assistant", "content": _ollama_txt or "今日费用超限，本地模型执行。请给出结论。"}}
                        ]
                    },
                    "tokens": 0,
                }
        except Exception as _dl_err:
            resp = {"success": False, "error": f"费用超限降级失败: {_dl_err}"}
    else:
        # 2026-09-06 修复3: 写类任务「只读侦察死循环」收敛 — 任务要求落盘(write_draft/草稿/write_file)
        # 但 tracker 无任何写入且已 ≥5 轮 → 注入强制收敛提醒(否则 agent 可侦察 40+ 步从不写,
        # 直到预算耗尽空回复收场, 既非假完成也非完成, 纯烧 token)。
        try:
            _loop_readonly_rounds = bridge_round
            _any_user_wants_write = any(
                _m.get("role") == "user"
                and any(
                    _kw in str(_m.get("content") or "")
                    for _kw in ("write_draft", "write_note", "write_file", "落盘", "调整草稿", "修改草稿", "草稿箱")
                )
                for _m in messages[-8:]
            )
            _trk_w5 = _session_write_tracker.get(session_id, {}) or {}
            _wrote5 = (
                _trk_w5.get("write_count", 0) > 0
                or _trk_w5.get("vault_write_count", 0) > 0
                or _trk_w5.get("execute_write_count", 0) > 0
            )
            _already_warned5 = any("仍在侦察" in str(_m.get("content") or "") for _m in messages[-4:])
            if _any_user_wants_write and not _wrote5 and _loop_readonly_rounds >= 5 and not _already_warned5:
                _steer5 = (
                    "[系统收敛] 本任务要求实际落盘(write_draft/write_file/write_note), 已侦察 %d 轮仍未调用任何写入工具。"
                    "停止继续读取资料——已有信息足够。立即执行写入: 抖音草稿用 obsidian_knowledge(action=write_draft, platform=抖音, title=草稿原名, content=修改后全文), "
                    "然后回读验证内容已变。再侦察而不写入会被判定为未完成任务。" % (_loop_readonly_rounds + 1)
                )
                messages.append({"role": "system", "content": _steer5})
                print(f"[READONLY_LOOP] 写类任务 {_loop_readonly_rounds + 1} 轮无写入, 注入收敛提醒")
        except Exception as _rol_e:
            print(f"[READONLY_LOOP] 收敛注入异常(忽略): {_rol_e}")
        # 2026-09-06 诊断: bridge 发送前 dump messages 结构(定位 reasoning 400)
        try:
            _bdbg = "; ".join(
                "%s(rc=%s tc=%d %s)"
                % (
                    m.get("role"),
                    "Y" if m.get("reasoning_content") is not None else "N",
                    len(m.get("tool_calls") or []),
                    str(m.get("content") or "")[:30],
                )
                for m in messages[-15:]
            )
            print(f"[BRIDGE_DUMP] round={bridge_round} n={len(messages)} :: {_bdbg[:1200]}", flush=True)
        except Exception:
            pass
        resp = adapter.execute_with_tools(
            messages=messages,
            tools=tools,
            user_id=user_id,
            temperature=0.7,
            max_tokens=mt_out,
            thinking=(thinking2 and not no_think),
        )
    # 降级: DeepSeek 402 欠费 → 本地 Ollama qwen2.5:7b
    if (
        resp
        and not resp.get("success")
        and ("402" in str(resp.get("error", "") or "") or "Insufficient Balance" in str(resp.get("error", "") or ""))
    ):
        try:
            print("[MODEL_FALLBACK] DeepSeek 402 → 降级本地 Ollama (tools_hint 文本模式)")
            is_7b_fallback = True
            from core.lib.llm_client import llm_client

            _tools_hint = "可用工具：\n" + "\n".join(
                [
                    f"- {t.get('function',{}).get('name','')}: {t.get('function',{}).get('description','')[:100]}"
                    for t in tools
                    if isinstance(t, dict) and t.get("function")
                ]
            )
            _user_prompt = str(data.get("message", "") if isinstance(data, dict) else "") or ""
            if not _user_prompt and isinstance(data, dict):
                for _m_d in reversed(data.get("messages", []) or []):
                    if isinstance(_m_d, dict) and _m_d.get("role") == "user" and _m_d.get("content"):
                        _user_prompt = str(_m_d.get("content", ""))
                        break
            if not _user_prompt:
                for _m_rev in reversed(messages):
                    if _m_rev.get("role") == "user" and _m_rev.get("content"):
                        _user_prompt = str(_m_rev.get("content", ""))
                        break
            _system_prompt = "你是 ClawsJoy 的执行助手，调用工具完成用户任务。"
            print(f"[7B_DEBUG] 消息角色序列: {[m.get('role','') for m in messages[-8:]]}")
            print(
                f"[7B_DEBUG] 最后一条user content: {repr(messages[-1].get('content','')[:200]) if messages[-1].get('role')=='user' else '最后一条不是user'}"
            )
            print(f"[7B_DEBUG] prompt={repr(_user_prompt)[:100]}")
            print(f"[7B_DEBUG] system={repr(_system_prompt)[:150]}")
            import json as _json7b_chat

            import requests as _req7b_chat

            # 7B 降级: system + user + 上一步工具结果(让 7B 知道已执行)
            _chat_msgs = [{"role": "system", "content": _system_prompt}]
            _chat_msgs.append({"role": "user", "content": _user_prompt})
            # 上一步工具结果注入(标准 tool role)
            _last_tc = last_7b_result
            if _last_tc:
                _chat_msgs.append({"role": "tool", "content": str(_last_tc)[:1500]})
                _chat_msgs.append({"role": "user", "content": "如果上面的工具结果已满足需求，请直接输出中文报告，不要再次调用工具。"})
            _r7b = _req7b_chat.post(
                "http://127.0.0.1:11434/api/chat",
                json={
                    "model": "qwen2.5:7b-instruct-q4_0-gpu",
                    "messages": _chat_msgs,
                    "tools": tools,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 512},
                },
                timeout=(30, 120),
            )
            _r7b_json = _r7b.json() if _r7b.status_code == 200 else {}
            _ollama_msg = _r7b_json.get("message", {}) or {}
            _ollama_text = str(_ollama_msg.get("content", "") or "")
            print(f"[7B_DEBUG] 消息数={len(_chat_msgs)} 最后3条角色={[m.get('role','') for m in _chat_msgs[-3:]]}")
            _tool_msgs_debug = [m for m in _chat_msgs if m.get("role") == "tool"]
            if _tool_msgs_debug:
                print(
                    f"[7B_DEBUG] tool消息数={len(_tool_msgs_debug)} 最后tool内容={_tool_msgs_debug[-1].get('content','')[:200]}"
                )
            else:
                print(f"[7B_DEBUG] 无tool消息")
            print(f"[7B_DEBUG] 原始文本: {repr(_ollama_text)[:200]}")
            # Ollama 原生 tools API: 直接读 tool_calls(不再正则找 JSON)
            _ollama_tool_calls = _ollama_msg.get("tool_calls") or []
            if _ollama_tool_calls:
                _tc0 = _ollama_tool_calls[0].get("function", {}) or {}
                _tc_name = str(_tc0.get("name", "")).strip()
                _tc_args = _tc0.get("arguments", {}) or {}
                if _tc_name:
                    resp = {
                        "success": True,
                        "data": {
                            "choices": [
                                {
                                    "message": {
                                        "role": "assistant",
                                        "content": "",
                                        "tool_calls": [
                                            {
                                                "id": "call_7b",
                                                "type": "function",
                                                "function": {"name": _tc_name, "arguments": _tc_args},
                                            }
                                        ],
                                    }
                                }
                            ]
                        },
                        "tokens": 0,
                    }
                    print(f"[7B_TOOLS_HINT] 原生tools解析: {_tc_name} args={_tc_args}")
                else:
                    resp = {
                        "success": True,
                        "data": {"choices": [{"message": {"role": "assistant", "content": _ollama_text}}]},
                        "tokens": 0,
                    }
            elif _ollama_text:
                # 无 tool_calls 但有文本 → 尝试从 content 提取 tool call JSON(7B 文本模式)
                import json as _j7b3
                import re as _r7b3

                _m3 = _r7b3.search(r'\{[^{}]*"name"\s*:\s*"[^"]+"[^{}]*\}', _ollama_text)
                if _m3:
                    try:
                        _tc3 = _j7b3.loads(_m3.group(0))
                        _n3 = str(_tc3.get("name", "")).strip()
                        if _n3:
                            resp = {
                                "success": True,
                                "data": {
                                    "choices": [
                                        {
                                            "message": {
                                                "role": "assistant",
                                                "content": "",
                                                "tool_calls": [
                                                    {
                                                        "id": "call_7b",
                                                        "type": "function",
                                                        "function": {
                                                            "name": _n3,
                                                            "arguments": _tc3.get("arguments", {}),
                                                        },
                                                    }
                                                ],
                                            }
                                        }
                                    ]
                                },
                                "tokens": 0,
                            }
                            print(f"[7B_TOOLS_HINT] content提取: {_n3} args={_tc3.get('arguments',{})}")
                        else:
                            resp = {
                                "success": True,
                                "data": {"choices": [{"message": {"role": "assistant", "content": _ollama_text}}]},
                                "tokens": 0,
                            }
                    except Exception:
                        resp = {
                            "success": True,
                            "data": {"choices": [{"message": {"role": "assistant", "content": _ollama_text}}]},
                            "tokens": 0,
                        }
                else:
                    resp = {
                        "success": True,
                        "data": {"choices": [{"message": {"role": "assistant", "content": _ollama_text}}]},
                        "tokens": 0,
                    }
            else:
                # 空回复 → 占位(触发空回复重试)
                resp = {
                    "success": True,
                    "data": {"choices": [{"message": {"role": "assistant", "content": ""}}]},
                    "tokens": 0,
                }

        except Exception as _fb_err:
            resp = {"success": False, "error": f"降级失败: {_fb_err}"}
    return resp, is_7b_fallback
