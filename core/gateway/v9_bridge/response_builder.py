# -*- coding: utf-8 -*-
"""P3-A 响应构建（从 _v9_bridge_loop post-loop 尾段归位，2026-09-12）。

桥接循环结束后的全部后处理：多文件规划约束 / 重试循环检测 / StandardJSON 适配 /
raw_arguments 展平 / 网关 write_file 拦截 / 交付物缺失检测 / 写入意图检测 /
统一注入 / 计划与 goal 上下文注入 / last_task / 自动归档 / 用户消息入库 /
tool_steps 回传 / Turn reason 计算 / 暂停分支。
"""
import json
from datetime import datetime
from pathlib import Path

from core.gateway.archive import _archive_asset, _archive_user_message
from core.gateway.context_validator import _classify_task_type, _is_plan_message, _is_readonly_task, _should_inject_hint
from core.gateway.execute_agent_task import _update_world_model
from core.gateway.path_utils import _resolve_path
from core.lib.gateway_helpers import _get_sandbox_base, cleanup_task_context
from core.lib.paths import runtime_tmp_path
from core.gateway import _proc as _proc  # ⭐ 窗隐唯一出口（PM 2026-10-05 令 · ⛔ 各写 creationflags）


def build_bridge_response(
    *,
    messages,
    data_resp,
    session_id,
    user_id,
    tokens,
    tool_steps,
    bridge_exhausted,
    round_exhausted,
    guard_paused,
    cancelled,
    empty_reply_count,
    bmsg,
    turn_id,
    current_plan,
    plan_status,
    data,
    file_retry_state,
    policy,
    build_tool_steps_summary_fn,
    goal_info_fn,
    write_turn_end_fn,
    ts_progress_fn,
):
    """P3-A 桥接响应构建：循环结束后产出最终 7 元组返回。

    原地契约：mutates messages(append 系统/上下文消息) 与 data_resp(content 注入 /
    tool_calls 清空)，不重建列表。返回
    (messages, tool_steps, bridge_exhausted, payload_or_None, tokens, turn_reason, turn_reason_detail)；
    暂停分支返回 payload 为 paused 字典的 7 元组，正常分支 payload 为 None。
    """

    msg = data_resp.get("choices", [{}])[0].get("message", {})

    # 多文件任务硬约束：涉及2+文件时，必须先输出规划文本
    _last_usr_hard = ""
    for _mh in messages:
        if _mh["role"] == "user":
            _last_usr_hard = _mh["content"]
    import re as _re_hard

    _file_matches_hard = _re_hard.findall(r"(?<![_])[\w_]+/\w+\.py|(?<![_])[\w_]+\.py", _last_usr_hard)
    if len(_file_matches_hard) >= 2:
        _has_plan = bool(msg.get("content", "").strip())
        _tool_calls_raw = msg.get("tool_calls", [])
        _has_write = any(
            tc.get("function", {}).get("name") in ("write_file", "write_large", "execute_command")
            for tc in _tool_calls_raw
        )
        if not _has_plan:
            _files_list = ", ".join(_file_matches_hard[:8])
            _plan_msg = f"【系统】检测到多文件任务，请先列出执行计划再修改。\n涉及文件: {_files_list}\n\n请按以下格式列出计划:\n1. 修改文件: [路径]\n2. 修改内容: [具体改动]\n3. 执行顺序: [步骤]\n\n列出计划后，系统将自动放行后续修改操作。"
            # P4 steer 全量迁移: 纠偏指令走 steer 通道(桥接循环轮起始 drain 注入)
            try:
                from core.gateway.shared_state import add_steer

                add_steer(session_id, _plan_msg)
            except Exception:
                messages.append({"role": "system", "content": _plan_msg})

            # 不 return，让流程继续走到 DeepSeek 调用

    # BUG 6: 重试循环检测
    from core.gateway.repeat_tool_reminder import detect_retry_loop

    detect_retry_loop(messages=messages, session_id=session_id)
    # 多文件任务强制确认：检测到计划消息时，丢弃 tool_calls 只保留计划文本
    _tool_calls_raw = msg.get("tool_calls", [])
    _has_write_calls = any(
        tc.get("function", {}).get("name") in ("write_file", "write_large", "execute_command") for tc in _tool_calls_raw
    )
    if _has_write_calls and _is_plan_message(msg.get("content", "")):
        msg["tool_calls"] = []
        messages.append({"role": "system", "content": "[系统] 已收到执行计划。请等待用户确认（回复'按此计划执行'或'继续'）后再动手修改。"})

    # StandardJSON 适配：将 OpenAI tool_calls 转换为 StandardJSON
    _tool_calls_raw = msg.get("tool_calls", [])
    if _tool_calls_raw:
        try:
            from core.lib.gateway_helpers import tool_calls_to_standard_json

            _standard_req = tool_calls_to_standard_json(_tool_calls_raw, user_id, session_id)
            # 注入到 messages 中供引擎层使用
            messages.append(
                {"role": "system", "content": f"[StandardJSON] {json.dumps(_standard_req, ensure_ascii=False)}"}
            )
        except Exception:
            pass

    # raw_arguments 展平：将 execute_command 的 raw_arguments 提取为顶层 command
    _tool_calls_raw = msg.get("tool_calls", [])
    for _tc in _tool_calls_raw:
        if _tc.get("function", {}).get("name") == "execute_command":
            try:
                _args = json.loads(_tc["function"]["arguments"])
                if "raw_arguments" in _args and "command" not in _args:
                    _raw = _args["raw_arguments"]
                    try:
                        _parsed = json.loads(_raw)
                        _args["command"] = _parsed.get("command", "")
                    except Exception:
                        import re as _re_flat

                        _match = _re_flat.search(r'"command"\s*:\s*"(.+?)\'PYEOF\'', _raw, _re_flat.DOTALL)
                        if _match:
                            _args["command"] = _match.group(1).rstrip() + "'PYEOF'"
                    _tc["function"]["arguments"] = json.dumps({"command": _args.get("command", "")})
            except Exception:
                pass

    # ★ 网关拦截 write_file：长内容直接从 Agent 响应中提取并写入
    _tool_calls = msg.get("tool_calls", [])
    for _tc in _tool_calls:
        if _tc.get("function", {}).get("name") in ("write_file", "write_large"):
            try:
                _args = json.loads(_tc["function"]["arguments"])
                _content = _args.get("content", "")
                _path = _args.get("path", "")
                if _content and len(_content) > 3000 and _path:
                    # 重试计数：同一文件连续写入时检测完整性
                    _retry_key = f"retry_{_path}"
                    _retry_count = file_retry_state.get(_retry_key, 0) + 1
                    file_retry_state[_retry_key] = _retry_count
                    _base = _get_sandbox_base(user_id, session_id)
                    _base.mkdir(parents=True, exist_ok=True)
                    _target = _resolve_path(_base, _path)
                    _target.parent.mkdir(parents=True, exist_ok=True)
                    _target.write_text(_content, encoding="utf-8")
                    _update_world_model(str(_target), _content, user_id, session_id)
                    # 写入后自动语法检测
                    import subprocess as _sp2

                    _syntax_result = _proc.run_hidden(
                        ["python3", "-c", f'compile(open("{_target}").read(), "{_target}", "exec")'],
                        capture_output=True,
                        text=True,
                        timeout=10, encoding="utf-8", errors="replace"
                    )
                    if _syntax_result.returncode != 0:
                        _args[
                            "content"
                        ] = f"[网关已写入但发现语法错误] {_syntax_result.stderr[:300]}\n请用 write_file 完整重写该文件，不要用 heredoc 逐段追加。"
                    else:
                        _defs = [l for l in _content.split("\n") if l.strip().startswith("def ")]
                        _classes = [l for l in _content.split("\n") if l.strip().startswith("class ")]
                        _summary = (
                            f"[长内容已由网关直接写入 {_target}，共 {len(_content)} 字符，{len(_classes)} 个类，{len(_defs)} 个方法，语法检查通过。"
                        )
                    if _retry_count >= policy["retry"]["write_retry_limit"]:
                        _summary += f" 该文件已连续写入 {_retry_count} 次，禁止使用 heredoc。请用 write_file 一次性完整重写全部内容。"
                    else:
                        _summary += " 如果文件内容不完整，请用 write_file 完整重写，不要用 heredoc 追加。"
                        _args["content"] = _summary
                    _tc["function"]["arguments"] = json.dumps(_args, ensure_ascii=False)
                    # 超长内容 (>5000字符) 引导走临时文件通道
                    if len(_content) > 5000:
                        import uuid as _uuid2

                        _temp_name = f"agent_write_{_uuid2.uuid4().hex[:12]}.py"
                        _temp_str = runtime_tmp_path("clawsjoy_temp", _temp_name)
                        _temp_path = Path(_temp_str)
                        _temp_path.parent.mkdir(parents=True, exist_ok=True)
                        _temp_path.write_text(_content, encoding="utf-8")
                        _args[
                            "content"
                        ] = f"[超长内容已写入临时文件] 请调用 write_finalize(path='{_path}', temp_path='{_temp_str}') 完成写入。"
                        _tc["function"]["arguments"] = json.dumps(_args, ensure_ascii=False)
            except Exception:
                pass

    # ★ 交付物缺失检测：目标文件未写入 + 最近 3 次都是读取 → 注入信号
    import re as _re5

    _target_files = set()
    _last_user = messages[-1]["content"] if messages[-1]["role"] == "user" else ""
    _main_match = _re5.search(r'(?:修改|创建|完善|写入|新增|添加|生成|实现|编写|补充|新建|在)\s*[`"\']?([\w_]+/[\w_]+\.\w+)', _last_user)
    if _main_match:
        _target_files = {_main_match.group(1)}
    _written_files = set()
    for _m in messages:
        if _m["role"] == "assistant":
            for _tc in _m.get("tool_calls", []):
                if _tc.get("function", {}).get("name") in ("write_file", "write_large", "execute_command"):
                    try:
                        _args = json.loads(_tc["function"]["arguments"])
                        if "path" in _args:
                            _written_files.add(_args["path"])
                    except Exception:
                        pass
    _assistant_msgs = [m for m in messages if m["role"] == "assistant"]
    _recent_actions = []
    for _am in _assistant_msgs[-3:]:
        for _tc in _am.get("tool_calls", []):
            _recent_actions.append(_tc["function"]["name"])
    if _target_files and not _target_files.issubset(_written_files):
        if _recent_actions and all(a in ("read_file", "list_dir", "search_files") for a in _recent_actions):
            _target_str = ", ".join(_target_files - _written_files)
            # P4 steer 全量迁移: 纠偏指令走 steer 通道
            try:
                from core.gateway.shared_state import add_steer

                add_steer(
                    session_id, f"[系统] 目标文件 {_target_str} 尚未写入，但你最近 3 次操作都是读取。世界模型已包含文件结构信息，请直接 write_file 写入，不要继续读取。"
                )
            except Exception:
                messages.append(
                    {
                        "role": "system",
                        "content": f"[系统] 目标文件 {_target_str} 尚未写入，但你最近 3 次操作都是读取。世界模型已包含文件结构信息，请直接 write_file 写入，不要继续读取。",
                    }
                )

    # 写入意图检测 v3：检测最后一轮是否只有读取、无写入/执行操作
    tool_calls = msg.get("tool_calls", [])
    READ_ONLY_TOOLS = {"read_file", "list_dir", "search_files", "query_index"}
    WRITE_OR_EXEC_TOOLS = {"write_file", "write_large", "execute_command"}
    WRITE_KEYWORDS = ["创建", "修改", "完善", "写入", "新增", "添加文件", "生成", "实现", "编写", "补充", "新建", "写", "加", "改", "补全"]
    user_msg = ""
    if messages:
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = m.get("content", "")
                break
    file_missing = True
    _user_msgs = [m for m in messages if m["role"] == "user"]
    if user_msg:
        has_write_intent = any(kw in user_msg for kw in WRITE_KEYWORDS)
        tool_names = {tc.get("function", {}).get("name") for tc in tool_calls} if tool_calls else set()
        is_read_only = (not tool_names) or tool_names.issubset(READ_ONLY_TOOLS)
        if has_write_intent and is_read_only:
            import re as _re

            path_match = _re.search(r"clawsjoy_dev/[\w/]+\.\w+", user_msg)
            target_path = path_match.group(0) if path_match else "目标文件"
            check_path = Path(f"data/projects/{user_id}/{session_id}") / target_path if path_match else None
            if file_missing:
                _last_usr_v9 = _user_msgs[-1]["content"] if _user_msgs else ""
                if not _is_readonly_task(_last_usr_v9):
                    _task_type = _classify_task_type(messages)
                    if _task_type == "analysis":
                        hint_msg = "[系统] 当前阶段：分析。请输出分析报告。\n"
                    else:
                        hint_msg = (
                            "[系统] 当前阶段：交付。请用 write_file 或 python3 heredoc 将修改写入文件。如果需要参考已有代码，直接写入后再用 read_file 验证。\n"
                        )
                    # 去重防卡死：最近 6 条消息中已含 2 次相同提示则不再注入
                    if _should_inject_hint(messages, hint_msg):
                        if msg.get("content"):
                            data_resp["choices"][0]["message"]["content"] = hint_msg + "\n\n" + msg["content"]
                        else:
                            data_resp["choices"][0]["message"]["content"] = hint_msg
    # ===== 统一注入点（方案二+三合并）：阶段提示 + 已读目标文件提示 =====
    from core.gateway.precision_inject import unified_inject

    unified_inject(messages=messages, data_resp=data_resp, is_read_only=is_read_only, file_missing=file_missing)
    # ===== 统一注入点结束 =====
    # #189 方案B：拦截分支注入当前计划到 messages，保持计划上下文
    if current_plan and plan_status:
        try:
            _plan_ctx = f"[系统] 当前计划状态：{plan_status}。当前计划：{str(current_plan)[:2000]}。请基于该计划继续执行，不要偏离计划内容。"
            if not any(_plan_ctx[:30] in str(_m.get("content", "")) for _m in messages if _m.get("role") == "system"):
                messages.append({"role": "system", "content": _plan_ctx})
        except Exception:
            pass
    # #101 G6 目标跨轮次持久：重启/新请求时恢复 goal 上下文注入
    try:
        from core.gateway.goal_state import goal_context_injection

        _goal_ctx = goal_context_injection(user_id, session_id)
        if _goal_ctx and not any(
            _goal_ctx[:20] in str(_m.get("content", "")) for _m in messages if _m.get("role") == "system"
        ):
            messages.append({"role": "system", "content": _goal_ctx})
    except Exception as _goal_ctx_err:
        print(f"[GOAL_STATE] 目标注入失败: {_goal_ctx_err}")

    # 更新 last_task
    try:
        _last_usr_v9 = ""
        for _mv9 in messages:
            if _mv9["role"] == "user":
                _last_usr_v9 = _mv9["content"]
        if _last_usr_v9:
            messages = cleanup_task_context(messages, _last_usr_v9[:80], user_id, session_id)
            # 批221 修（DS-206-3 指认：本处原为**读-改-写非原子直写** ⇒ 与其它写者并发交错 ⇒ 损坏）。
            # 切到统一原子出口（按路径锁 + tmp + os.replace + 容错读）。
            from core.gateway.state_json import update_json as _uj_v9
            _sf_v9 = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")

            def _mut_v9(_d):
                _d["last_task"] = _last_usr_v9[:200]
                _d["last_time"] = datetime.now().isoformat()

            _uj_v9(_sf_v9, _mut_v9)
    except Exception:
        pass

    # #155 自动归档执行计划：检测最后一条 assistant 消息是否包含步骤列表/执行计划
    try:
        from core.lib.code_entity_extractor import extractor as _step_extractor

        _last_assistant_msg = ""
        for _m_v9 in reversed(messages):
            if _m_v9.get("role") == "assistant":
                _last_assistant_msg = _m_v9.get("content", "") or ""
                break
        if _last_assistant_msg and ("步骤列表" in _last_assistant_msg or "执行计划" in _last_assistant_msg):
            import re as _re_steps

            _step_lines = []
            for _sl in _last_assistant_msg.splitlines():
                _sl_stripped = _sl.strip()
                if not _sl_stripped:
                    continue
                if _re_steps.match(r"^(\d+[.、）)]|[-*•])\s*\S", _sl_stripped) or _re_steps.match(
                    r"^步骤\s*\d*[一二三四五六七八九十]?\s*[：:]", _sl_stripped
                ):
                    _step_lines.append(_sl_stripped)
            if not _step_lines:
                _step_lines = [_last_assistant_msg[:500]]
            _task_name = f"{session_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            for _idx_v9, _step_v9 in enumerate(_step_lines, 1):
                _step_extractor.store_step_summary(
                    task_name=_task_name,
                    step_number=_idx_v9,
                    summary_json={
                        "content": _step_v9[:1000],
                        "source": "v9_agent_chat",
                        "ts": datetime.now().isoformat(),
                    },
                )
            print(f"[AUTO_ARCHIVE_PLAN] 已归档 {len(_step_lines)} 步 -> {_task_name}")
    except Exception as _e_v9:
        print(f"[AUTO_ARCHIVE_PLAN] 失败: {_e_v9}")

    # ===== #145 数字资产自动文件化：检测最后一条 assistant 消息是否包含计划/报告/决策 =====
    try:
        _last_assistant_v9 = ""
        for _m_v9 in reversed(messages):
            if _m_v9.get("role") == "assistant" and _m_v9.get("content"):
                _last_assistant_v9 = str(_m_v9["content"])
                break
        if _last_assistant_v9:
            _kind_v9 = None
            _plan_markers = ["执行计划", "步骤列表", "修改计划", "实施步骤", "开发路线"]
            _report_markers = ["分析报告", "排查报告", "审计报告", "核查结论", "盘点结果", "结论如下", "报告如下", "方案如下", "设计方案"]
            _decision_markers = ["决策如下", "决策建议", "最终决策", "选定方案", "决定采用", "决定使用", "决策结果", "方案已定"]
            if _is_plan_message(_last_assistant_v9) or any(_mk in _last_assistant_v9 for _mk in _plan_markers):
                _kind_v9 = "plan"
            elif any(_mk in _last_assistant_v9 for _mk in _decision_markers):
                _kind_v9 = "decision"
            elif any(_mk in _last_assistant_v9 for _mk in _report_markers):
                _kind_v9 = "report"
            if _kind_v9:
                _title_v9 = " ".join(_last_assistant_v9.split())[:100]
                _archived_v9 = _archive_asset(_kind_v9, session_id, _title_v9, _last_assistant_v9[:4000], messages)
                if _archived_v9:
                    print(f"[AUTO_ARCHIVE] v9_agent_chat 触发 {_kind_v9} 归档 -> {_archived_v9}")
    except Exception as _e_v9ar:
        print(f"[AUTO_ARCHIVE] v9_agent_chat 归档失败: {_e_v9ar}")

    # #166 用户消息自动入库 SAG + JSONL：每轮对话后归档最后一条 user 消息
    try:
        _last_user_v9 = ""
        for _m_v9 in reversed(messages):
            if _m_v9.get("role") == "user":
                _last_user_v9 = str(_m_v9.get("content", "") or "")
                break
        if _last_user_v9:
            _archive_user_message(
                "user", _last_user_v9, session_id, (data or {}).get("agent_name", ""), (data or {}).get("user_id", "")
            )
    except Exception as _e_um9:
        print(f"[USER_MSG_ARCHIVE] v9_agent_chat 归档失败: {_e_um9}")

    # #101 桥接工具步骤回传：注入最终 message（前端 agentSend 渲染工具使用记录）
    # max_tokens 空产出修复: 记录是否"既无 content 也无 tool_steps"(→ reason 降级 error)
    _exhausted_no_output = False
    try:
        _bmsg_final = (data_resp or {}).get("choices", [{}])[0].get("message", {}) or {}
        if tool_steps:
            _bmsg_final["tool_steps"] = tool_steps
        # #103 O1 防重复：跑满 8 轮时，返回的 tool_calls 已由服务端执行，
        # 清空避免前端 agentSend 重复执行（双保险：前端还按 bridge_exhausted 跳过）
        if bridge_exhausted:
            # P0-3: done payload 的 message 取自 messages 列表(_loop_data2),
            # 必须清空 messages 里最后一条 assistant 的 tool_calls, 否则前端
            # 按 msg.tool_calls 走 continue 死循环重发(双保险)。
            # P1-1: 8轮自然耗尽 - 明确引导 LLM 输出评估结论, 不再调工具
            # max_tokens 空产出修复: 最终 content 为空 → 基于 tool_steps 提取摘要(不调 LLM)
            _final_empty = not str(_bmsg_final.get("content") or "").strip()
            _step_summary = ""
            if _final_empty and tool_steps:
                _step_summary = build_tool_steps_summary_fn(tool_steps)
            if _final_empty and not tool_steps:
                _exhausted_no_output = True
            if round_exhausted:
                _round_msg = "\n\n[系统] 已达轮次上限，请基于现有信息输出评估结论，不要继续调用工具。"
                _new_content = (_step_summary or str(_bmsg_final.get("content") or "")) + _round_msg
                for _m_r in reversed(messages):
                    if _m_r.get("role") == "assistant":
                        if _m_r.get("tool_calls"):
                            _m_r["tool_calls"] = []
                        _m_r["content"] = _new_content
                        break
                _bmsg_final["tool_calls"] = []
                _bmsg_final["content"] = _new_content
            else:
                _round_msg2 = "\n\n[系统] 已达单轮最大工具调用数，工具已由服务端执行。如需继续请说明下一步。"
                _new_content2 = (_step_summary or str(_bmsg_final.get("content") or "")) + _round_msg2
                for _m_r in reversed(messages):
                    if _m_r.get("role") == "assistant":
                        if _m_r.get("tool_calls"):
                            _m_r["tool_calls"] = []
                        _m_r["content"] = _new_content2
                        break
                _bmsg_final["tool_calls"] = []
                _bmsg_final["content"] = _new_content2
    except Exception as _ts_err:
        print(f"[V9_BRIDGE] tool_steps 注入失败: {_ts_err}")
    # Turn 协议 Step1: 统一 reason 计算(turn_protocol 单一事实来源)
    from core.gateway.turn_protocol import _compute_turn_reason as _ctr

    _turn_reason, _turn_reason_detail = _ctr(
        cancelled=cancelled,
        guard_paused=guard_paused,
        exhausted_no_output=_exhausted_no_output,
        round_exhausted=round_exhausted,
        bridge_exhausted=bridge_exhausted,
        empty_reply_count=empty_reply_count,
        content=str(bmsg.get("content") or ""),
    )
    # 报告持久化: 优先最终 LLM 总结(_bmsg_final.content), 其次 tool_steps 摘要
    _turn_report = ""
    try:
        _turn_report = str(_bmsg_final.get("content") or "").strip()
        if not _turn_report and tool_steps:
            _turn_report = build_tool_steps_summary_fn(tool_steps)
    except Exception:
        _turn_report = ""
    write_turn_end_fn(
        session_id,
        turn_id,
        tokens,
        _turn_reason,
        _turn_reason_detail,
        len(tool_steps),
        report=_turn_report or None,
        messages=messages,
        tool_steps=tool_steps,
    )
    if guard_paused:
        # P1: 暂停 → 返回明确状态 + 恢复选项(continue_messages 带"换策略"系统指令)
        _pause_msg = {"role": "system", "content": "[系统] 连续失败 8 次已暂停。请换一种实现方式(更换工具/路径/策略)，不要重复被拒操作；如确需继续，说明理由后重新尝试。"}
        _pause_bp = None
        try:
            from core.gateway.execute_agent_task import _pause_recursion as _pr_pause

            _last_step_p = tool_steps[-1] if tool_steps else {}
            _pause_bp = _pr_pause(
                session_id, str(_last_step_p.get("tool", "")), str(_last_step_p.get("arg") or ""), _turn_reason_detail
            )
        except Exception:
            pass
        _pause_msgs = messages + [_pause_msg]
        return (
            _pause_msgs,
            tool_steps,
            True,
            {
                "success": True,
                "status": "paused",
                "reason": "paused",
                "reason_detail": _turn_reason_detail,
                "message": "连续失败 8 次已暂停。可选择继续执行(换策略)、修改任务或停止。",
                "tool_steps": tool_steps,
                "paused_breakpoint": _pause_bp,
                "continue_messages": _pause_msgs,
                "goal_info": goal_info_fn(session_id),
                "progress": ts_progress_fn(),
                "tokens": tokens,
            },
            tokens,
            _turn_reason,
            _turn_reason_detail,
        )
    return (messages, tool_steps, bridge_exhausted, None, tokens, _turn_reason, _turn_reason_detail)
