# -*- coding: utf-8 -*-
"""P3-B 恢复层（从 v9_agent_chat 654- 归位，2026-09-12）。

分块（块=函数，全部在本模块）：
  A recover_session            回执分发 + 讨论/确认路由 + 上下文清理
  B build_prompt               api_key + 异步入队 + 复杂度预判 + prompt 组装   (待拆)
  C inject_context_and_flags   前置检测 + 上下文注入 + 确认检测/继续恢复       (待拆)
  D preload_code_and_history   清缓存 + task_progress + 历史步骤 + 代码预加载  (待拆)
  E build_tools_and_trim       tools 构建/过滤/截断/压缩 + 兜底 + 清空·恢复    (待拆)
  F prepare_thinking_and_messages  thinking 按需 + prepare_request             (待拆)
  G orchestrate_goal           goal/steer/contract 编排（整块不可切）          (待拆)

契约：
1. 每块返回 dict；short_circuit 非 None → 薄路由 jsonify 后 return。
2. 层内**不 import flask**（短路一律返回信号）。
3. messages 由块返回（链式传递），块内不读闭包。
4. 依赖函数以 fn 参数传入（防循环 import）。
"""
import json
import os
import threading as _threading
import time
from pathlib import Path

from core.gateway.message_assembler import _inject_sys_content

# B 块(2026-09-13): 续跑上下文兜底链（goal 原文 / 请求体历史 / BRIEF 补生成）
from core.gateway.resume_context import is_resume_utterance as _is_resume_utterance
from core.gateway.resume_context import resolve_task_text
from core.gateway.shared_state import (
    _consecutive_lists,
    _consecutive_reads,
    _read_cache,
    _session_artifacts,
    _session_failed,
)
from core.gateway.v9_bridge.context_utils import _v9_is_resume_utterance
from core.gateway.write_gate import _plan_pending


def recover_session(
    *,
    data,
    messages,
    model,
    user_id,
    session_id,
    restore_pending_fn,
    handle_approvals_fn,
    check_discuss_budget_fn,
    execute_agent_task_fn,
    cleanup_ctx_fn,
):
    """块 A：pending 恢复 + 回执分发 + 讨论/确认路由 + 上下文清理。

    契约：返回 {short_circuit, messages, plan_status, current_plan}；
    short_circuit 非 None → 路由 jsonify 后 return；messages 为清理后的新列表。
    """
    try:
        restore_pending_fn(user_id, session_id)
    except Exception:
        pass

    _approve_resp = handle_approvals_fn(data, messages, model, user_id, session_id)
    if _approve_resp is not None:
        return {"short_circuit": _approve_resp, "messages": messages, "plan_status": None, "current_plan": None}

    # 编排 Agent 多轮讨论路由
    plan_status = data.get("plan_status", "")
    current_plan = data.get("current_plan")
    if plan_status == "discussing" and current_plan:
        _agent_name = data.get("agent_name", "")
        _model = ""
        try:
            from core.lib.v8.roster_engine import roster_engine

            _member = roster_engine.get("default", _agent_name)
            if _member:
                _model = _member.get("model", "")
        except Exception:
            pass
        if _model and _model.startswith("deepseek"):
            import os as _os

            if not _os.getenv("DEEPSEEK_API_KEY"):
                _model = "ollama"
        _over, _used, _limit = check_discuss_budget_fn(user_id, data.get("server_id", "default"), _model)
        if _over:
            print(f"[BUDGET] 讨论预算超限: {_used}/{_limit}")
            return {
                "short_circuit": {
                    "plan_status": "confirmed",
                    "message": f"今日 Token 预算已超限({_used}/{_limit})，自动确认计划。",
                    "current_plan": current_plan,
                },
                "messages": messages,
                "plan_status": plan_status,
                "current_plan": current_plan,
            }
        from core.lib.v8.task_orchestrator import orchestrator

        result = orchestrator.discuss_plan(
            user_message=messages[-1]["content"] if messages else "",
            current_plan=current_plan,
            user_id=user_id,
            server_id="default",
        )
        return {"short_circuit": result, "messages": messages, "plan_status": plan_status, "current_plan": current_plan}
    if plan_status == "confirmed" and current_plan:
        _task_id = f"task_{int(time.time())}"
        _plan = current_plan
        _plan["user_id"] = user_id
        _plan["session_id"] = session_id
        import threading as _th_plan

        _th_plan.Thread(
            target=execute_agent_task_fn,
            args=(
                user_id,
                session_id,
                [{"role": "system", "content": f"执行已确认的计划：{json.dumps(_plan, ensure_ascii=False)}"}],
                model,
                _task_id,
                data.get("sub_task_id"),
            ),
            daemon=True,
        ).start()
        return {
            "short_circuit": {"status": "executing", "task_id": _task_id, "message": "计划已确认，V9 异步执行已启动。"},
            "messages": messages,
            "plan_status": plan_status,
            "current_plan": current_plan,
        }

    # 统一上下文清理
    _task_name_async = ""
    for _m in messages:
        if _m["role"] == "user":
            _task_name_async = _m["content"][:80]
            break
    messages = cleanup_ctx_fn(messages, _task_name_async, user_id, session_id)
    return {"short_circuit": None, "messages": messages, "plan_status": plan_status, "current_plan": current_plan}


def build_tools_and_trim(
    *,
    messages,
    tools,
    model,
    user_id,
    session_id,
    state_file,
    get_agent_tools_fn,
    filter_tools_fn,
    calc_token_budget_fn,
    tg_estimate_fn,
    compress_fn,
    validate_fn,
    hard_truncate_fn,
    estimate_tokens_fn,
    max_context_tokens,
    get_sandbox_base_fn,
):
    """块 E：tools 构建/阶段门/模式过滤 + 400KB·350KB 智能截断 + token 预算复查 + 分层·极端压缩 + 兜底命令。

    契约：返回 {short_circuit, messages, tools}；short_circuit 非 None → 路由 jsonify 后 return。
    R7：三套阈值(400KB 字节 / max_context_tokens*0.75 token / 截断后 tg_estimate vs budget)原样并存，不合并不重排。
    """
    tools = get_agent_tools_fn()
    # F0.2a: verifying 阶段只保留验证/修复工具, 隐藏研究工具
    try:
        from core.gateway.task_contract import contract_for_session as _cfs_v

        _c_v = _cfs_v(session_id)
        if _c_v and (_c_v.get("phase") or "") == "verifying":
            _rs_tools = (
                "web_search",
                "fetch_web",
                "browse_web",
                "browser_local",
                "playwright_browser",
                "browser_hybrid",
                "table_extract",
            )
            _before_n = len(tools)
            tools = [t for t in tools if not (t.get("function", {}).get("name") in _rs_tools)]
            if len(tools) != _before_n:
                print("[PHASE_GATE] verifying 阶段隐藏研究工具")
    except Exception:
        pass
    # P1: 按当前模式过滤 tools schema — LLM 看不到 search_files/list_dir 等不可用工具, 不再试错
    tools = filter_tools_fn(tools, session_id, messages)
    _msg_size = len(json.dumps(messages, ensure_ascii=False))
    if _msg_size > 400 * 1024:
        system_msgs = [m for m in messages if m["role"] == "system"]
        learning_msgs = [
            m for m in messages if "clawsjoy_dev/" in str(m.get("content", "")) and m["role"] in ("user", "assistant")
        ]
        # [#191] tail 去重 + system 全部前置：排除 system 与已包含在 learning_msgs 中的消息
        # [#192] tail:2 类型感知：最近一条是 tool 结果时回溯到最近一条 assistant 回复
        _win_start = max(0, len(messages) - 3)
        _last_msg_obj = messages[-1] if messages else None
        if _last_msg_obj and _last_msg_obj.get("role") == "tool":
            for _i in range(len(messages) - 2, -1, -1):
                if messages[_i].get("role") == "assistant":
                    _win_start = max(0, _i - 1)
                    break
        tail = [m for m in messages[_win_start:] if m["role"] != "system" and m not in learning_msgs[-5:]]
        # 改为：保留最近的 tool 消息
        tool_msgs = [m for m in messages[-10:] if m.get("role") == "tool"]
        messages = system_msgs + tool_msgs + learning_msgs[-3:] + tail
        print(
            f"[V9] 🔴 请求体 {_msg_size//1024}KB 超过 400KB，已智能截断至 {len(messages)} 条（sys:{len(system_msgs)} learn:{min(len(learning_msgs),5)} tail:{len(tail)}）"
        )
        # [#191] 截断后必须重算字节：设 350KB 安全线，超限继续截断
        _msg_size2 = len(json.dumps(messages, ensure_ascii=False))
        if _msg_size2 > 350 * 1024:
            messages = compress_fn(messages, user_id, session_id, keep=8)
            messages = validate_fn(messages)
            _msg_size2 = len(json.dumps(messages, ensure_ascii=False))
            print(f"[V9] 🔴 截断后重算 {_msg_size2//1024}KB 仍超 350KB 安全线，已继续压缩至 {len(messages)} 条")
    # [400KB 截断后强制复查] tg_estimate(messages, tools) 与 budget 比较（统一预算基准）
    _budget_check = calc_token_budget_fn(model, tools)
    _est_check = tg_estimate_fn(messages, tools)
    if _est_check > _budget_check:
        print(f"[V9] 🔴 400KB 截断后复查：tg_estimate(messages, tools)={_est_check} > budget={_budget_check}，继续压缩")
        messages = compress_fn(messages, user_id, session_id, keep=10)
        messages = hard_truncate_fn(messages, _budget_check)
        messages = validate_fn(messages)
        _est_check2 = tg_estimate_fn(messages, tools)
        print(f"[V9] 复查压缩后：{_est_check} → {_est_check2} (budget={_budget_check})")
    else:
        print(f"[V9] ✅ 400KB 截断后复查通过：tg_estimate(messages, tools)={_est_check} ≤ budget={_budget_check}")
    if estimate_tokens_fn(messages) > max_context_tokens * 0.75:
        # 分层压缩策略：循环降级直到 token 安全
        for _keep in [15, 10, 8, 5]:
            messages = compress_fn(messages, user_id, session_id, keep=_keep)
            messages = hard_truncate_fn(messages, calc_token_budget_fn(model, tools))
            messages = validate_fn(messages)
            print(f"[V9] ⚠️ 上下文接近上限，已压缩至 {len(messages)} 条 (keep={_keep})")
            if estimate_tokens_fn(messages) <= max_context_tokens * 0.75:
                break

    # 压缩后 tokens 验证：用 _estimate_tokens 重新检查
    if estimate_tokens_fn(messages) > max_context_tokens * 0.75:
        # 极端压缩：只保留 system + 最后 2 条
        head = [m for m in messages if m["role"] == "system"]
        tail = [m for m in messages[-10:] if m.get("role") == "tool"] or messages[-2:]
        messages = head + tail
        print(f"[V9] 🔴 极端压缩：仅保留 {len(head)} 条 system + {len(tail)} 条最近消息")

    # tools 已在上方（400KB 截断前）提前构建

    # 构建 tools 之后
    if state_file.exists():
        try:
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))

            except Exception:
                state = {}
            if state.get("skip_exploration"):
                tools = [t for t in tools if t["function"]["name"] not in ("list_dir", "search_files")]
        except Exception:
            pass

    # 兜底拦截前端指令
    if messages and messages[-1]["role"] == "user":
        last_msg = messages[-1]["content"].strip().upper()
        if last_msg in ("/CLEAN", "/CLEAR"):
            return {
                "short_circuit": {"success": True, "data": {"choices": [{"message": {"content": "✅ 已清空"}}]}},
                "messages": messages,
                "tools": tools,
            }
        if last_msg == "/RESTORE":
            base = get_sandbox_base_fn(user_id, session_id)
            restored = []
            for bak in base.rglob("*.bak"):
                orig = bak.with_suffix("")
                orig.write_text(bak.read_text(encoding="utf-8"), encoding="utf-8")
                bak.unlink()
                restored.append(str(orig.name))
            return {
                "short_circuit": {
                    "success": True,
                    "data": {
                        "choices": [{"message": {"content": f"✅ 已恢复: {', '.join(restored) if restored else '无备份文件'}"}}]
                    },
                },
                "messages": messages,
                "tools": tools,
            }
    return {"short_circuit": None, "messages": messages, "tools": tools}


def prepare_thinking(*, messages):
    """块 F：thinking 按需判定（默认关；含 分析/推理/设计/规划/复杂推理/深度思考/reasoning/design 才开）。

    契约：返回 {thinking2, file_think, last_usr_think}。
    注：thinking2 / file_think 在本块内首次赋值（不是入参）——按 E 块教训，调用处不得传入。
    """
    _thinking2 = False
    import re as _re_think

    _last_usr_think = ""
    for _mt in messages:
        if _mt["role"] == "user":
            _last_usr_think = _mt["content"]
    _file_think = _re_think.findall(r"[\w_]+/\w+\.py|[\w_]+\.py", _last_usr_think)
    # ===== P0 费用保护: thinking 按需(默认关; 含 分析/推理/设计/规划/复杂 关键词才开) =====
    try:
        from core.gateway.shared_state import _load_v9_execution_policy as _l9p2

        _eb_p0 = (_l9p2() or {}).get("execution_budget", {}) or {}
        _think_default = bool(_eb_p0.get("thinking_enabled", False))
    except Exception:
        _think_default = False
    _think_kw = ("分析", "推理", "设计", "规划", "复杂推理", "深度思考", "reasoning", "design")
    _need_think = _think_default or any(k in str(_last_usr_think or "") for k in _think_kw)
    _thinking2 = _need_think  # 默认关; 复杂任务才开
    return {"thinking2": _thinking2, "file_think": _file_think, "last_usr_think": _last_usr_think}


def inject_context_and_flags(
    *,
    messages,
    user_id,
    session_id,
    task_id,
    inject_ctx_fn,
    mark_plan_fn,
    round_checkpoint_fn,
    looks_like_new_task_fn,
    gsl_events_fn,
):
    """块 C：上下文注入 + 确认检测/继续恢复/新任务隔离 + 轮检查点 + 多文件检测。

    契约：返回 {short_circuit, messages}；short_circuit 非 None → 路由 jsonify 后 return。
    注：原块在本层内直接调 _v9_inject_context/_v9_mark_agent_plan/_v9_round_checkpoint，
        为防循环 import 一律以 fn 参数传入。
    """
    messages = inject_ctx_fn(messages, user_id, session_id)

    messages = mark_plan_fn(messages, task_id)
    # fastText 确认检测：替换关键词列表（H1 修复：_last_usr_confirm 先初始化再使用，原顺序颠倒致 NameError 被吞）
    _confirm_kw_legacy = [
        "按此计划",
        "确认执行",
        "执行计划",
        "开始执行",
        "继续",
        "继续执行",
        "接着做",
        "下一步",
        "好的",
        "可以",
        "行",
        "开始吧",
        "动手",
        "搞",
        "整",
        "干",
        "来吧",
        "走",
        "执行",
        "确定",
        "确认",
    ]
    _last_usr_confirm = ""
    for _mp in messages:
        if _mp["role"] == "user":
            _last_usr_confirm = _mp["content"]
    try:
        from core.agents.cortex import _get_ft_model

        _ft = _get_ft_model()
        _label, _conf = _ft.predict(_last_usr_confirm.strip())
        _is_confirm = _label[0] == "__label__confirm_plan" and _conf[0] > 0.7
    except Exception:
        _is_confirm = False
    # 增强："继续"指令上下文恢复（BRIEF.md 接入）
    if _last_usr_confirm.strip().lower() in ("继续", "/continue", "继续任务"):
        try:
            # 检查上次任务是否已完成
            _state_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
            if _state_file.exists():
                try:
                    _state = json.loads(_state_file.read_text(encoding="utf-8"))
                    if _state.get("last_task_status") == "done":
                        return {
                            "short_circuit": {"reply": "上次任务已完成。请下达新指令。", "status": "previous_done"},
                            "messages": messages,
                        }
                except Exception:
                    pass
            from core.lib.brief_manager import get_brief_manager

            _brief = get_brief_manager(user_id, session_id).inject()
            if _brief:
                messages.append({"role": "system", "content": f"[上下文恢复] 任务说明书（BRIEF.md）：\n{_brief}"})
            else:
                # no_context 修复(2026-09-11) 组3兜底: BRIEF.md 空 → 回退 .agent_state.json last_task 降级注入
                _fallback_task = ""
                _fb_src = "state.last_task"
                try:
                    _fb_state = json.loads(_state_file.read_text(encoding="utf-8")) if _state_file.exists() else {}
                    _fallback_task = str(_fb_state.get("last_task", "") or "")
                except Exception:
                    _fallback_task = ""
                # B 块(2026-09-13) 兜底链扩容 —— no_context 触发条件收窄到「真的一个源都没有」。
                # 历史事故(第三次同型): 预算耗尽轮在 agent_gateway_enhanced.py:479-481 被
                # _budget_limit_guard 早退 → 跳过 core/gateway/memory.py 之 persist_session_learning_state() / response_builder.py:250 两个
                # 唯一的 last_task 写入点 → 该文件里只剩 goal 字段; BRIEF.md 又只在
                # execute_agent_task.py:415 生成(PA 走 /v9/agent/chat, 从不调用它) →
                # 老板回「继续」时两个源全空 → 当场报 no_context, 任务链断。
                # 这里补三个**同一现场就有**的源(goal 目标原文 / 请求体自带的 messages 历史),
                # 并把"继续"这种噪音值挡掉(此前 last_task 可能被写成"继续"本身)。来源留痕。
                if not _fallback_task or _is_resume_utterance(_fallback_task):
                    _fb_task2, _fb_src2 = resolve_task_text(messages=messages, user_id=user_id, session_id=session_id)
                    _fallback_task = _fb_task2 or ""
                    _fb_src = _fb_src2 or "none"
                if _fallback_task:
                    messages.append(
                        {"role": "system", "content": f"[上下文恢复(降级)] 上次任务摘要（来源：{_fb_src}）：\n{_fallback_task}"}
                    )
                    print(f"[RESUME_CTX] 「继续」恢复上下文 来源={_fb_src} len={len(_fallback_task)}")
                else:
                    return {
                        "short_circuit": {"reply": "上下文丢失，请重新下达指令。（可直接把任务原文再发一次，我会接着做）", "error": "no_context"},
                        "messages": messages,
                    }
        except Exception:
            return {"short_circuit": {"reply": "状态文件损坏，请重新下达指令。", "error": "corrupted"}, "messages": messages}
    # (c)2026-09-05 新任务上下文隔离: 长新任务文本(POC 等含「继续/下一步」词但长度>12
    # 且非 继续/恢复 开头)不视为旧任务确认 → 跳过旧任务/计划注入, 防上下文串扰
    _ut_v9 = _last_usr_confirm.strip()
    _is_long_new_task = looks_like_new_task_fn(_ut_v9)
    # "继续"任务恢复：无计划时自动注入最近任务
    if not _is_long_new_task and (len(_ut_v9) <= 4 or _is_confirm or any(kw in _ut_v9 for kw in _confirm_kw_legacy)):
        # 先尝试恢复计划标记
        _last_plan = ""
        for _mp in reversed(messages):
            if _mp["role"] == "assistant" and _mp.get("content"):
                _c = _mp["content"]
                if "<!-- CLAWSJOY_PLAN -->" in _c:
                    _last_plan = _c.replace("<!-- CLAWSJOY_PLAN -->", "")[-2000:]
                    break
        if _last_plan:
            messages.append({"role": "system", "content": f"[系统] 用户确认执行以下计划（✅ 表示已完成），请严格按照计划步骤执行，不要偏离：\n{_last_plan}"})
        else:
            # 无计划标记时，恢复最近一次用户任务
            _st_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
            _last_task = (
                (
                    json.loads(_st_file.read_text(encoding="utf-8")).get("last_task")
                    or json.loads(_st_file.read_text(encoding="utf-8")).get("_last_task", "")
                )
                if _st_file.exists()
                else ""
            )
            if _last_task:
                messages.append({"role": "system", "content": f"[系统] 当前任务：{_last_task}"})

    # (2026-09-05) 计划确认/续跑轮: 注入本任务已执行工具摘要, 防整轮重复侦察烧 token
    # (实测: blocked 计划确认后执行轮把 obsidian/list/read/curl 整轮重跑, 2 轮烧 ~420K)
    # S2(2026-09-05): 记忆单点化 — round_checkpoint(合并 L0 recon-digest/L2 轮摘要/L3 步骤断点)
    if not _is_long_new_task:
        try:
            from core.gateway.session_log import get_session_log as _gsl_dig

            _cp = round_checkpoint_fn(gsl_events_fn(session_id)._events)
            if _cp:
                messages.append({"role": "system", "content": _cp})
        except Exception:
            pass

    # 多文件任务检测：追加规划模板
    import re as _re_plan

    _last_usr_plan = ""
    for _mp in messages:
        if _mp["role"] == "user" and not str(_mp.get("content", "")).startswith("[系统]"):
            _last_usr_plan = _mp["content"]
    _file_matches = _re_plan.findall(r"(?<![_])[\w_]+/\w+\.py|(?<![_])[\w_]+\.py", _last_usr_plan)
    if len(_file_matches) >= 2:
        _inject_sys_content(
            messages,
            (
                "\n【多文件任务 — 请先列出执行计划】\n"
                "涉及文件: " + ", ".join(_file_matches[:8]) + "\n"
                "请按以下格式列出计划后，再执行修改:\n"
                "1. 修改文件: [文件路径]\n"
                "2. 修改内容: [具体改动]\n"
                "3. 执行顺序: [步骤]\n"
                "列出计划后等待确认，不要直接修改。"
            ),
        )
    return {"short_circuit": None, "messages": messages}


def preload_code_and_history(*, data, messages, user_id, session_id):
    """块 D：新任务清缓存 + task_progress 注入 + 历史步骤 + artifact 摘要 + 代码预加载。

    契约：返回 {short_circuit, messages}；short_circuit 非 None → 路由 jsonify 后 return。
    R4：5 个状态(_read_cache/_consecutive_reads/_consecutive_lists/_session_failed/_session_artifacts)
        统一 from core.gateway.shared_state import —— 单点持有、同一对象、无副本。
    R5：代码预加载的 session 依赖一律走入参 user_id/session_id，不读闭包。
    """
    # 新任务开始，清空 read_file 缓存，重置计数器
    # #210 新任务开始，清除失败锁定
    _session_failed.pop(data.get("session_id", ""), None)
    _read_cache.clear()
    # #106 C1 并发修复：per-session 重置
    _consecutive_reads[data.get("session_id", "default")] = 0
    _consecutive_lists[data.get("session_id", "default")] = 0

    # 从 .agent_state.json 注入 task_progress
    try:
        state_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
        if state_file.exists():
            try:
                agent_state = json.loads(state_file.read_text(encoding="utf-8"))

            except Exception:
                agent_state = {}
            tp = agent_state.get("task_progress")
            if tp:
                summary = "\n【系统】以下信息来自之前的任务记录：\n"
                for step in tp.get("completed_steps", []):
                    summary += f"- {step.get('action')}: {step.get('file', '')}\n"
                if tp.get("pending_steps"):
                    summary += f"待完成: {', '.join(tp['pending_steps'])}\n"
                # #166 防假完成：上次任务验证未通过时明确警告，避免误导后续 Agent
                _vc_info = tp.get("verification", {}) or {}
                if tp.get("last_action") == "failed" or _vc_info.get("passed") is False:
                    _vc_fail_txt = "；".join(_vc_info.get("failures", []))[:300]
                    summary += "⚠️ 警告：上次任务完成验证未通过（last_action=failed）！\n"
                    if _vc_fail_txt:
                        summary += f"失败原因: {_vc_fail_txt}\n"
                    summary += "不得将上次任务视为已完成，需重新执行并真正通过验证。\n"
                issues = agent_state.get("known_issues", [])
                if issues:
                    summary += "已知问题:\n"
                    for i in issues[:3]:
                        summary += f"- {i.get('issue', str(i))}\n"
                tips = agent_state.get("optimization_tips", "")
                if tips:
                    summary += f"\n💡 优化建议: {tips}\n"
                _inject_sys_content(messages, summary)
    except Exception:
        pass

    # 注入历史任务步骤
    try:
        state_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
        if state_file.exists():
            try:
                agent_state = json.loads(state_file.read_text(encoding="utf-8"))

            except Exception:
                agent_state = {}
            tp = agent_state.get("task_progress")
            if tp and tp.get("completed_steps"):
                hint = "\n[系统] 以下步骤已在之前任务中完成，无需重复执行：\n"
                for s in tp["completed_steps"]:
                    if s.get("action") == "verified" and s.get("status") == "already_correct":
                        hint += "- 已验证代码处于目标状态，不需要修改\n"
                    else:
                        hint += f"- {s.get('file', '')} {s.get('action', '')}\n"
                hint += "\n请直接执行验证步骤，不要重新读取或修改代码。\n"
                hint += "验证方式：python3 -c 运行断言，不要用 pytest。"
                print(f"[V9] 历史任务注入: {len(tp.get('completed_steps',[]))} 步骤")
                if len(messages) > 0 and messages[-1]["role"] == "user":
                    messages[-1]["content"] = hint + "\n\n" + messages[-1]["content"]
                else:
                    _inject_sys_content(messages, hint)
    except Exception:
        pass

    # artifact 摘要注入
    _session_key = f"{user_id}/{session_id}"
    if _session_key in _session_artifacts:
        arts = _session_artifacts[_session_key]
        snapshots = [a for a in arts if a["type"] == "file_snapshot"]
        modifications = [a for a in arts if a["type"] == "file_modification"]
        if snapshots or modifications:
            summary = "\n【本次会话已执行的操作】\n"
            if snapshots:
                files = list(set(a["file"] for a in snapshots))
                summary += f"已读文件: {', '.join(files)}\n"
            if modifications:
                files = list(set(a["file"] for a in modifications))
                summary += f"已修改文件: {', '.join(files)}\n"
            summary += "不要重复读取或修改已完成的操作。"
            _inject_sys_content(messages, summary)

    # ===== 代码预加载（用户级懒加载索引 + 关键词匹配 + embedding 精排） =====
    if messages and messages[-1]["role"] == "user":
        print("[V9] Preload triggered")
        try:
            from pathlib import Path as _Path

            sandbox_base = _Path(f"data/projects/{user_id}/{session_id}")
            project_dir = sandbox_base if (sandbox_base).exists() else sandbox_base

            from core.lib.code_indexer import CodeIndexer

            indexer = CodeIndexer(project_root=str(project_dir))
            _code_indexer = indexer  # 模块级变量，供 _execute_sandbox_tool 使用

            index_file = project_dir / "data" / "code_index" / "keyword_index.json"
            print(f"[V9] index_file path: {index_file} exists: {index_file.exists()}")

            # 首次使用：同步初始化索引（空项目直接跳过）
            if not index_file.exists():
                print(f"[V9] First use, initializing code index...")
                indexer.auto_init()
                indexer._save()
                # 不返回 initializing，空项目直接进入任务

            if not indexer._keyword_index:
                indexer._load()

            # 检测是否需要中文关键词（首次会调 DeepSeek）

            kw_status = indexer._ensure_chinese_keywords()
            if kw_status.get("status") == "initializing":
                return jsonify(
                    {
                        "success": True,
                        "status": "initializing",
                        "message": "正在生成代码中文索引，请稍候...预计 3-5 秒",
                        "data": {"choices": [{"message": {"content": "🔧 正在生成代码中文索引，请稍候..."}}]},
                    }
                )

            task = messages[-1]["content"]
            matched_files = indexer.search_files(task, limit=5)

            if matched_files:
                top_blocks = indexer.search_blocks(task, files=matched_files, limit=5)
                files_to_load = list(set(b.get("file", "") for b in top_blocks if b.get("file")))
                if not files_to_load:
                    files_to_load = matched_files[:3]

                preload = "\n\n【项目代码 — 已自动加载，无需 read_file】\n"
                for f in files_to_load:
                    try:
                        file_path = project_dir / f
                        if file_path.exists():
                            file_content = file_path.read_text(encoding="utf-8")[:2000]
                            preload += f"\n--- {f} ---\n{file_content}\n"
                    except Exception:
                        pass

                if "---" in preload:
                    if messages[0]["role"] == "system":
                        _inject_sys_content(messages, preload)

        except Exception as e:
            print(f"[V9] Code preload failed (non-fatal): {e}")
    # ===== 预加载结束 =====
    return {"short_circuit": None, "messages": messages}


def build_prompt(
    *, data, messages, model, user_id, session_id, allowed_commands, deepseek_key_loaded, execute_agent_task_fn
):
    """块 B：api_key 校验 + 异步入队 + 复杂度预判 + prompt 模板组装。

    契约：返回 {short_circuit, messages, api_key, state_file, task_id}。
      short_circuit 非 None → 路由 jsonify 后 return（后续键可能未产生，调用方须先判短路再解包）。
    R6：allowed_commands / deepseek_key_loaded 为模块只读常量，以参数传入（已查证无写入）。
    注1：filled_prompt / sandbox_root 在本块内产出并同块内耗尽，不是对外产出。
    注2：**kw 不是产出** —— 它只是 B 内推导式的循环变量(Store)，词边界搜索会误收；
         上一版把它放进返回 dict 导致 return 时 NameError（本轮真实故障根因，已剔除）。
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        return {
            "short_circuit": {
                "success": False,
                "error": f"Key丢失! 启动时={'已加载' if deepseek_key_loaded.startswith('sk-') else '未加载'}，请求时为空",
                "loaded_at_startup": deepseek_key_loaded[:15] + "..."
                if deepseek_key_loaded.startswith("sk-")
                else deepseek_key_loaded,
            },
            "messages": messages,
        }

    # 异步模式：启动后台任务
    async_mode = data.get("async", False)
    task_id = data.get("task_id", "")

    if async_mode and task_id and messages and messages[-1]["role"] == "user":
        _threading.Thread(
            target=execute_agent_task_fn,
            args=(user_id, session_id, messages, model, task_id, data.get("sub_task_id")),
            daemon=True,
        ).start()
        return {
            "short_circuit": {
                "success": True,
                "status": "started",
                "task_id": task_id,
                "message": "任务已启动，可通过 /v9/task/<task_id> 查询状态",
            },
            "messages": messages,
        }

    # 复杂度预判：≥2个文件或≥3个修改意图时注入规划指令
    if messages and messages[-1]["role"] == "user":
        import re as _re

        user_msg = messages[-1]["content"]
        # 匹配 agent 名称模式（calculator_agent、analysis_agent 等）
        agent_count = len(_re.findall(r"\w+_agent", user_msg))
        # 匹配文件路径模式（agents/xxx/xxx.py 或 tools/xxx.py）
        file_count = len(_re.findall(r"(?:agents|tools)/[\w/]+\.py", user_msg))
        # 修改意图关键词
        modify_intents = sum(1 for kw in ["修改", "改", "重构", "提取", "统一", "合并", "拆分", "迁移"] if kw in user_msg)
        # 用户显式要求直接执行(给完成边界/命令式) → 不注入确认; 用户自己要确认 → 保留确认
        _user_wants_direct = any(
            k in user_msg
            for k in [
                "直接执行",
                "直接做",
                "实际落盘",
                "实际写",
                "用 write_draft 实际写",
                "必须 write_draft",
                "完成条件",
                "直接写",
                "直接修改",
                "请直接",
                "直接完成",
            ]
        )
        _user_wants_confirm = any(
            k in user_msg for k in ["请您确认", "请确认", "等确认", "确认后执行", "确认后再执行", "先列计划", "请你先列", "请先列"]
        )
        _complex_code = agent_count >= 2 or file_count >= 2 or modify_intents >= 3
        if _complex_code and not _user_wants_direct:
            if _user_wants_confirm or file_count >= 2 or agent_count >= 2:
                messages[-1]["content"] = user_msg + "\n\n[系统指令] 此任务涉及多个文件或步骤，请先列出修改计划，询问用户确认后再执行。"
            else:
                messages[-1]["content"] = (
                    user_msg + "\n\n[系统指令] 此任务修改点较多，请先用几行列出执行要点(目标文件+改动点)，然后立即执行完成落盘并回读验证；不要停在计划阶段等待确认——任务完成以实际写入为准。"
                )

    # 加载 Prompt 模板
    prompt_template = Path("config/prompts/agent_system.md").read_text(encoding="utf-8")
    # 注入工具声明段（#150）：替换 <!-- TOOL_DECLARATIONS_START/END --> 占位标记
    try:
        from core.lib.v8.loop_context_manager import LoopContextManager

        prompt_template = LoopContextManager()._inject_tool_declarations(prompt_template)
    except Exception:
        pass

    sandbox_root = Path(f"data/projects/{user_id}/{session_id}").resolve()
    state_file = sandbox_root / "clawsjoy_dev" / ".agent_state.json"
    last_summary = ""
    venv_path = ".venv"
    project_root = "clawsjoy_dev"

    if state_file.exists():
        try:
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))

            except Exception:
                state = {}
        except Exception:
            state = {}
        venv_path = state.get("venv_path", ".venv")
        project_root = state.get("project_root", "clawsjoy_dev")
        installed = state.get("installed_packages", [])
        issues = state.get("known_issues", [])
        last_summary = f"上次任务：{state.get('last_task','')}。"
        if installed:
            last_summary += f"已安装包：{', '.join(installed[:8])}。"
        if issues:
            last_summary += f"已知问题：{'；'.join([i.get('issue', str(i)) for i in issues[:3]])}。"

    filled_prompt = prompt_template
    filled_prompt = filled_prompt.replace("{sandbox_root}", str(sandbox_root))
    filled_prompt = filled_prompt.replace("{venv_path}", venv_path)
    filled_prompt = filled_prompt.replace("{project_root}", project_root)
    filled_prompt = filled_prompt.replace("{last_session_summary}", last_summary or "无")
    filled_prompt = filled_prompt.replace("{allowed_commands}", ", ".join(allowed_commands))

    if messages and messages[0]["role"] == "system":
        messages[0]["content"] = filled_prompt
    else:
        messages.insert(0, {"role": "system", "content": filled_prompt})

    # 前置检测：目标文件是否已满足任务需求（v9_agent_chat 同步路径）
    if messages and messages[-1]["role"] == "user":
        _last_usr = messages[-1]["content"]
        import re as _re_pre2

        _write_kw2 = ["添加", "创建", "修改", "新增", "加入", "实现", "编写", "补充"]
        if any(kw in _last_usr for kw in _write_kw2):
            _tgt = _re_pre2.search(r"[\w_]+/[\w_]+\.\w+", _last_usr)
            if _tgt:
                _tgt_file = _tgt.group(0)
                _base2 = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev")
                _disk_paths2 = [
                    _base2 / _tgt_file,
                    _base2 / "clawsjoy_dev" / _tgt_file,
                ]
                _proj_dir = _base2 / "clawsjoy_dev"
                if _proj_dir.exists():
                    for _sd in _proj_dir.iterdir():
                        if _sd.is_dir() and not _sd.name.startswith(".") and _sd.name not in ("data", "code_index"):
                            _disk_paths2.append(_sd / _tgt_file)
                _found2 = None
                for _dp2 in _disk_paths2:
                    if _dp2.exists():
                        _found2 = _dp2
                        break
                if not _found2:
                    import glob as _glob2

                    _fname2 = _tgt_file.split("/")[-1]
                    _candidates2 = _glob2.glob(str(_base2 / "**" / _fname2), recursive=True)
                    for _c2 in _candidates2:
                        _cp2 = Path(_c2)
                        if _cp2.exists() and "resume-optimizer" in str(_cp2):
                            _found2 = _cp2
                            break
                    if not _found2:
                        for _c2 in _candidates2:
                            _cp2 = Path(_c2)
                            if _cp2.exists():
                                _found2 = _cp2
                                break
                if _found2:
                    try:
                        import ast as _ast_pre2

                        _fc = _found2.read_text(encoding="utf-8")
                        if _found2.suffix == ".py":
                            _ast_pre2.parse(_fc)
                        # 前置检测防误判：计划文本不作为"文件已包含功能"依据
                        _plan_prefixes2 = ("执行计划", "修改计划", "任务计划", "实施计划", "开发路线", "步骤列表", "实施步骤")
                        _is_plan_text2 = _last_usr.strip().startswith(_plan_prefixes2) or any(
                            _pp2 in _last_usr[:40] for _pp2 in _plan_prefixes2
                        )
                        _kw_raw2 = _re_pre2.sub(r"[^一-鿿a-zA-Z0-9]", " ", _last_usr if not _is_plan_text2 else "")
                        _kw2 = _re_pre2.findall(r"[一-鿿]{2,}|[a-zA-Z_]{3,}", _kw_raw2)
                        _noise2 = {"resume", "optimizer", "analysis_page", "py", "markdown", "文件", "点击后将", "分析结果导出为"}
                        _action_pre2 = {
                            "添加",
                            "创建",
                            "修改",
                            "删除",
                            "新增",
                            "加入",
                            "实现",
                            "编写",
                            "补充",
                            "完善",
                            "中添加",
                            "点击后",
                            "分析结果导出",
                            "点击后将分析结果导出为",
                        }
                        _kw2 = [
                            k
                            for k in _kw2
                            if k.lower() not in _noise2 and k not in _action_pre2 and not (k.isascii() and k.isalpha())
                        ]
                        _matched2 = sum(1 for k in _kw2 if k.lower() in _fc.lower())
                        if _kw2 and _matched2 >= max(2, len(_kw2) * 0.5):
                            print(f"[v9_agent_chat] 前置检测命中但继续执行真实任务：目标文件已包含功能（{', '.join(_kw2[:5])}）")

                    except (SyntaxError, UnicodeDecodeError):
                        pass
    return {
        "short_circuit": None,
        "messages": messages,
        "api_key": api_key,
        "state_file": state_file,
        "task_id": task_id,
    }


def orchestrate_goal(
    *, data, messages, user_id, session_id, max_total_tools, load_policy_fn, plan_pending, is_resume_fn
):
    """块 G：goal/steer/contract 编排 + 新任务清理 + 桥接状态初始化。

    铁律（P3-B 历史教训，不得违反）：
      1. 整块不可切：create_goal / ensure_contract / add_steer / 清理 必须同处本函数；
      2. 归恢复层，不入桥接层：只做「该不该续跑 / 建不建 goal / 注不注 steer」的判定；
      3. 保持现状相对顺序：逐行照搬，不趁机理顺。
    契约：返回 {messages, bridge_exhausted}。
    注：_goal_continue 在本块内首次赋值（非入参）——按 E 块教训，调用处不得传入。
    """
    _goal_continue = bool(data.get("continue_goal"))
    try:
        from core.gateway.goal_state import create_goal, get_goal_by_session_id

        _last_user_goal = ""
        for _m_goal in reversed(messages):
            if _m_goal.get("role") == "user":
                _last_user_goal = str(_m_goal.get("content", ""))[:300]
                break
        if _goal_continue:
            _g_existing = get_goal_by_session_id(session_id)
            if _g_existing is None:
                print("[GOAL_STATE] continue_goal 但无现有 goal, 回退新建")
                _goal_continue = False
            else:
                print(f"[GOAL_STATE] 续跑 goal {str(_g_existing.get('goal_id'))[-12:]} (跳过 objective 覆盖)")
        # (b)2026-09-05: 「继续」短文本或显式 goal_id → 复用最近 goal 续跑, 不新建
        # (消除 UI 把「继续」当新任务 → 幽灵 goal objective=继续 的问题)
        if not _goal_continue and _last_user_goal:
            _resume_ut = is_resume_fn(_last_user_goal)
            _gid_req = str(data.get("goal_id") or "").strip()
            if _resume_ut or _gid_req:
                _g_cur = get_goal_by_session_id(session_id)
                if _g_cur is not None and _g_cur.get("status") in ("active", "paused", "failed"):
                    _goal_continue = True
                    print(
                        f"[GOAL_STATE] {('继续文本' if _resume_ut else 'goal_id=' + _gid_req)} → 复用 goal {str(_g_cur.get('goal_id'))[-12:]} 续跑, 不新建"
                    )
        if _last_user_goal and not _goal_continue:
            _g_plan = (plan_pending.get(session_id, {}) or {}).get("plan", "") if plan_pending.get(session_id) else ""
            _g_created = create_goal(
                user_id, session_id, _last_user_goal, plan=_g_plan or None, task_id=data.get("task_id", "")
            )
            # Goal 驱动多 turn: 无 plan 时 total 默认 = max_total_tools × goal_max_turns(工具预算×轮数)
            try:
                if _g_created and not _g_created.get("plan"):
                    from core.gateway.goal_state import update_goal_progress

                    _gmt = int(
                        ((load_policy_fn() or {}).get("execution_budget", {}) or {}).get("goal_max_turns", 5) or 5
                    )
                    _gtotal = int(max_total_tools) * _gmt
                    update_goal_progress(user_id, session_id, done=0, total=_gtotal)
                    print(f"[GOAL_STATE] 无 plan goal total 默认 {_gmt} 轮 × {max_total_tools} 工具 = {_gtotal}")
            except Exception as _gt_err:
                print(f"[GOAL_STATE] total 默认写入失败: {_gt_err}")
    except Exception as _goal_create_err:
        print(f"[GOAL_STATE] 目标创建失败: {_goal_create_err}")
    # F0.2b-resume(2026-09-09): 续跑老 goal 也补契约, 让 phase gate/evidence 对续跑生效
    try:
        from core.gateway.goal_state import get_goal_by_session_id as _gg_r
        from core.gateway.task_contract import contract_for_session as _cfs_r
        from core.gateway.task_contract import ensure_contract as _ec_r

        _gr_r = _gg_r(session_id)
        if _goal_continue and _gr_r and _cfs_r(session_id) is None:
            _gobj_r = str(_gr_r.get("objective") or "").strip()
            if _gobj_r:
                _tid_r = str(_gr_r.get("goal_id") or "") or ("task_" + str(int(time.time())))
                _cc_r = _ec_r(session_id, _tid_r, _gobj_r)
                if _cc_r:
                    print("[CONTRACT] 续跑补契约 " + str(session_id) + " phase=" + str(_cc_r.get("phase")))
    except Exception as _ecr_e:
        print("[CONTRACT] 续跑补契约异常(忽略): " + str(_ecr_e))

    # Goal 驱动多 turn: 每 turn 注入 steer "继续目标 X，已完成 a/b 步"(走 P4 add_steer 通道,
    # bridge_loop 轮起始 drain_steer 消费注入; 仅续跑且 goal 未完成时)
    try:
        from core.gateway.goal_state import get_goal_by_session_id
        from core.gateway.shared_state import add_steer

        _g_turn = get_goal_by_session_id(session_id)
        if _goal_continue and _g_turn and _g_turn.get("status") == "active":
            _gp_t = _g_turn.get("progress") or {}
            _gd_t = int(_gp_t.get("done", 0) or 0)
            _gt_t = int(_gp_t.get("total", 1) or 1)
            # 2026-09-09 续跑上下文注入修复: steer 必须带目标原文(此前只注入 goal_id →
            # Agent 看不到任务描述只能乱逛/考古; 与 GPT 指出的 goal 续跑错配同根因)。
            _gobj = str(_g_turn.get("objective") or "").strip()
            if not _gobj:
                # 兜底: 从契约取 objective
                try:
                    from core.gateway.task_contract import contract_for_session as _cfs_go

                    _cc_go = _cfs_go(session_id)
                    if _cc_go:
                        _gobj = str(_cc_go.get("objective") or "")
                except Exception:
                    pass
            _gobj_txt = ("，目标任务原文: " + _gobj[:400]) if _gobj else ""
            _mismatch_note = ""
            try:
                # 若当前用户消息像新任务且与目标原文不一致 → 提示停下询问, 不自行搜索猜测
                _cur_ut = ""
                for _m_go in reversed(messages):
                    if _m_go.get("role") == "user" and str(_m_go.get("content") or "").strip():
                        _cur_ut = str(_m_go.get("content") or "")
                        break
                if (
                    _gobj
                    and _cur_ut
                    and not _cur_ut.startswith("[系统]")
                    and len(_cur_ut) > 40
                    and _gobj[:60] not in _cur_ut
                ):
                    _mismatch_note = "。注意: 你当前收到的任务文本与目标原文不一致——若这是新任务请立即停下向老板确认，" "不要自行搜索猜测目标内容"
            except Exception:
                pass
            add_steer(
                session_id,
                f"继续目标 {str(_g_turn.get('goal_id',''))[-12:]}{_gobj_txt}，已完成 {_gd_t}/{_gt_t} 步。请基于上方目标原文与已有进度继续执行，不要重复已完成步骤{_mismatch_note}。",
            )
    except Exception as _steer_err:
        print(f"[GOAL_STATE] 续跑 steer 注入失败: {_steer_err}")
    # #1 协作取消: 新任务开始清旧取消标记(防误杀新任务)
    try:
        from core.gateway.shared_state import reset_cancel

        reset_cancel(session_id)
    except Exception:
        pass
    # #2 运行时上下文投影: 新任务清指纹缓存(强制首轮注入快照)
    try:
        from core.gateway.context_projection import reset_context_projection

        reset_context_projection(session_id)
    except Exception:
        pass
    # #103 O1 防重复：默认假设跑满 8 轮（工具已由服务端执行），正常 break 时置 False
    _bridge_exhausted = True
    return {"messages": messages, "bridge_exhausted": _bridge_exhausted}
