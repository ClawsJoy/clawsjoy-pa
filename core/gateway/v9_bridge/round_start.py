# -*- coding: utf-8 -*-
"""S6-A 轮首上下文重建+注入（从 _v9_bridge_loop 归位，2026-09-12）。"""


def rebuild_context(*, messages, tools, user_id, session_id, model, is_7b_fallback):
    """S6-A 轮首上下文重建+注入：derive + finalize + compress + steer + memory + precision + 沙箱边界。

    契约：返回 messages（重绑）。
    """
    from core.lib.gateway_helpers import _get_sandbox_base

    # B 块(2026-09-13): 记住重建前的 messages —— derive 会把恢复层刚注入的续跑上下文
    # (BRIEF/任务原文, 只存在于内存、没写成 session_log 事件)整个丢掉, 重建后要回挂。
    _incoming_before_derive = list(messages or [])
    # P2b 切换读取: 每轮从事件日志重建 messages(derive_messages 唯一入口)
    try:
        from core.gateway.session_log import get_session_log

        # R5(2026-08-31): 任务级上下文隔离 — 只投影最近一次真实用户消息之后的事件,
        # 历史任务 tool 输出(3935 条)不再累积 → 每轮 input 从 48K 降到当前任务量级
        messages = get_session_log(session_id).derive_messages(last_task_only=True)
    except Exception:
        pass
    # ===== B 块(2026-09-13) 续跑上下文回挂 =====
    # 事故(第三次同型): v9_chat/recovery.py 在「继续」轮把 [上下文恢复] 注入 messages,
    # 但 _v9_bridge_loop 轮首第一件事就是本函数 derive 重建 → 注入的消息在**第一次 LLM
    # 调用前**就被丢掉了(注入只改内存, 不写 session_log 事件) → 「续跑不丢上下文」形同虚设。
    # 这里把带续跑标记的 system 消息搬回(窄口径: 只认固定标记前缀 + 去重, 不做通用 system 合并)。
    try:
        _RESUME_MARKS = ("[上下文恢复", "[系统] 当前任务：", "[系统] 用户确认执行以下计划")
        _existing_heads = [str(_m.get("content") or "")[:24] for _m in messages if isinstance(_m, dict)]
        _keep_resume = []
        for _m_r in _incoming_before_derive:
            if not isinstance(_m_r, dict) or _m_r.get("role") != "system":
                continue
            _c_r = str(_m_r.get("content") or "")
            if not _c_r.startswith(_RESUME_MARKS):
                continue
            if _c_r[:24] in _existing_heads:
                continue
            if any(str(_k.get("content") or "")[:24] == _c_r[:24] for _k in _keep_resume):
                continue
            _keep_resume.append(_m_r)
        if _keep_resume:
            messages = messages + _keep_resume
            print(f"[RESUME_CTX] 轮首 derive 重建后回挂续跑上下文 {len(_keep_resume)} 条")
        # ===== 批65 A(a 方案)：系统提示词**无条件回挂**（扩大口径，只认首位那一条）=====
        # 事故（批59 发现 / 批61 定性 / 批63 立测）：entry.py:72-73 由 build_prompt 组装的
        # messages[0] 是系统提示词（config/prompts/agent_system.md），而上面那条窄口径只认
        # 3 个 _RESUME_MARKS 前缀 → SYS 不匹配 → derive 整体替换时**每轮丢失**。
        # 丢失的是约束类段落（工具声明段 / 执行纪律 G1-G3 / 防幻觉硬约束 / 禁止行为 /
        # 代码修改强制验证）→ 表现为**行为漂移而非报错**（静默丢失）。
        # A2 实测（批63/64）：SYS = 7,848 token/轮；含 SYS 后压缩阈值带下移 7,848，
        # 但 8 轮轨迹实测越阈值轮数不变（0→0）→ **不改变压缩行为**，故可独立落地。
        # 口径：只取重建前**首位**且 role==system 的一条（不泛化到所有 system，避免重复注入）；
        # 位置：回挂到 **messages[0]**（系统提示词须在首位，不与上面追加式的续跑标记混放）；
        # 去重：沿用 [:24] 前缀截断比较。
        _sys_head = _incoming_before_derive[0] if _incoming_before_derive else None
        if isinstance(_sys_head, dict) and _sys_head.get("role") == "system":
            _c_s = str(_sys_head.get("content") or "")
            _dup_sys = _c_s[:24] in _existing_heads or any(
                str(_m.get("content") or "")[:24] == _c_s[:24] for _m in messages if isinstance(_m, dict)
            )
            if _c_s and not _dup_sys:
                messages = [_sys_head] + list(messages)
                print(f"[RESUME_CTX] 系统提示词回挂 messages[0]({len(_c_s)} 字节)")
    except Exception as _rc_r_e:
        print(f"[RESUME_CTX] 续跑上下文回挂失败(不阻断): {_rc_r_e}")
    # 唯一出口: derive 重建会丢 reasoning_content(tool_calls assistant 必须带该字段,
    # 否则 DeepSeek 400 "reasoning_content must be passed back") — 重建后立即 finalize
    # P0 inbox: 每轮开始消费 steer 通道(纠偏/失败提示 → 注入下一轮 LLM 输入, 仅本轮)
    try:
        from core.gateway.message_assembler import _finalize_messages

        messages = _finalize_messages(messages)
        # 降本修复: derive 重建后每轮压缩(治 token 爆炸——入口压缩被 derive 绕过)
        from core.gateway.message_assembler import _calc_token_budget, _compress_messages, _tg_estimate

        _est_round = _tg_estimate(messages, tools)
        _budget_round = _calc_token_budget(model, tools)
        # #24 compaction 0.8 移植(2026-08-29): thresholdRatio 自动压缩(替代错误的 >300000 跳过)
        # 7B 降级: 本地免费 + 上下文小, 跳过压缩
        if is_7b_fallback:
            print(f"[V9] 7B降级跳过压缩 est={_est_round}")
            pass
        else:
            try:
                from core.gateway.shared_state import _load_v9_execution_policy as _l9c24

                _ratio_24 = float(
                    ((_l9c24() or {}).get("execution_budget", {}) or {}).get("compaction_threshold", 0.6) or 0.6
                )
            except Exception:
                _ratio_24 = 0.6
            _threshold_24 = _budget_round * _ratio_24  # 如 budget=61536 → 阈值≈49228
            if _est_round > _threshold_24:
                # 动态 keep: 目标=阈值的70% / 平均每条约token, 下限4 上限8
                _n_msgs_24 = max(len(messages), 1)
                _avg_24 = max(_est_round / _n_msgs_24, 1)
                _target_24 = _threshold_24 * 0.7
                _keep_24 = max(min(int(_target_24 / _avg_24), 8), 4)
                print(f"[COMPACT] est={_est_round} > 阈值{int(_threshold_24)}({_ratio_24}), 压缩 keep={_keep_24}")
                # #13 P1: 压缩前 token 快照(支持回滚) — #12 审核: tool_calls 内层深拷贝
                _snap_13 = {
                    "msgs": [
                        dict(m, tool_calls=[dict(tc) for tc in (m.get("tool_calls") or [])])
                        if m.get("tool_calls")
                        else dict(m)
                        for m in messages
                    ],
                    "est": _est_round,
                    "n": len(messages),
                }
                # 压缩前提取最近 tool 消息(7B/模型需要看到工具结果)
                _recent_tool_msgs = [m for m in messages[-10:] if m.get("role") == "tool"]
                messages = _compress_messages(messages, user_id, session_id, keep=_keep_24)
                # #7 审核修复: tool 加回前估算 — 超限则不加(保留压缩结果, tool 由下轮 derive 恢复)
                if _recent_tool_msgs:
                    _est_with_tool = _tg_estimate(messages + _recent_tool_msgs[-2:], tools)
                    if _est_with_tool <= _budget_round * 0.95:
                        messages.extend(_recent_tool_msgs[-2:])
                    else:
                        print(f"[COMPACT] tool 加回会超限({_est_with_tool}), 跳过加回")
                messages = _finalize_messages(messages)
                _est_after_24 = _tg_estimate(messages, tools)
                # #13 P1: 压缩异常(未降或反增) → 回滚快照
                if _est_after_24 >= _snap_13["est"] * 0.95 and _snap_13["n"] > 10:
                    print(f"[SNAPSHOT] 压缩未降效({_est_round}->{_est_after_24}), 回滚快照(keep={_keep_24})")
                    messages = _snap_13["msgs"]
                    _est_after_24 = _snap_13["est"]
                print(f"[COMPACT] 压缩后 est={_est_after_24}")
                # 压缩后仍超预算 → 硬截断(防 input 100万)
                if _est_after_24 > _budget_round * 0.95:
                    from core.gateway.message_assembler import _hard_truncate_messages

                    messages = _hard_truncate_messages(messages, max_tokens=int(_budget_round * 0.9))
                    messages = _finalize_messages(messages)
                    print(f"[COMPACT] 硬截断后 est={_tg_estimate(messages, tools)}")
    except Exception:
        pass
    try:
        from core.gateway.shared_state import drain_steer

        _steer_msgs = drain_steer(session_id)
        if _steer_msgs:
            for _sm in _steer_msgs:
                print(f"[STEER_INJECT] {str(_sm)[:80]}")
            messages = messages + [{"role": "user", "content": str(_s)[:500]} for _s in _steer_msgs]
    except Exception:
        pass
    # 跨 session 记忆: 每轮注入用户级 known_issues/known_patterns(messages 每轮重建, 幂等去重)
    try:
        from core.gateway.memory import get_memory_context as _mem_ctx

        _mem_txt = _mem_ctx(user_id)
        if _mem_txt and not any(str(m.get("content", "")).startswith("【跨会话记忆】") for m in messages):
            messages = messages + [{"role": "system", "content": f"【跨会话记忆】{_mem_txt}"}]
    except Exception:
        pass
    # D4 单一真源(2026-08-30): 每轮开始把 vault SOP 同步到沙箱 docs/reports 镜像 —
    # vault 是唯一真源, 镜像只读, 防三份副本漂移(5005 事件根因)。幂等: 内容相同跳过。
    try:
        from core.gateway.precision_inject import sync_knowledge_to_sandbox as _sync_kb

        _sync_kb(_get_sandbox_base(user_id, session_id))
    except Exception:
        pass
    # 精准上下文注入(Obsidian vault/SAG/Vector/memory 多源检索, 幂等去重): 任务语义 → 相关 top5
    try:
        from core.gateway.precision_inject import get_precision_context as _pctx

        _pctx_txt = _pctx(messages, user_id, session_id, _get_sandbox_base(user_id, session_id))
        if _pctx_txt and not any(str(m.get("content", "")).startswith("【精准上下文】") for m in messages):
            messages = messages + [{"role": "system", "content": _pctx_txt}]
    except Exception:
        pass
    # 沙箱边界提示: 所有文件必须写在 clawsjoy_dev/ 内, 禁止 /tmp 等系统路径(幂等去重)
    try:
        if not any(str(m.get("content", "")).startswith("【沙箱边界】") for m in messages):
            messages = messages + [
                {
                    "role": "system",
                    "content": "【沙箱边界】当前沙箱目录是 clawsjoy_dev/，所有文件必须写在此目录内（用相对路径，如 data/x.txt）。需要临时文件时用 data/tmp/ 目录（系统已创建，相对路径 data/tmp/xxx 即可）；报告写 data/reports/。禁止使用 /tmp、/home、/etc 等系统路径或绝对路径写入。PIL 生成中文图片直接用 /usr/share/fonts/truetype/wqy/wqy-microhei.ttc（已验证可用），不要探测系统字体目录（会被拦截）。",
                }
            ]
    except Exception:
        pass
    return messages
