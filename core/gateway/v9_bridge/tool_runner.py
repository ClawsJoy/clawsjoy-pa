# -*- coding: utf-8 -*-
"""S6-D 工具执行池化编排（从 _v9_bridge_loop 归位，2026-09-12）。"""


# ===== 续跑期间「禁写 vault」统一守卫（2026-09-13）=====
# 为什么必须统一：vault 写有三条互不相同的通道 ——
#   ① obsidian_knowledge 的写类 action（core/lib/gateway_helpers.py 的 _handle_obsidian_knowledge）
#   ② cu_learning 的 persist_sop（直调 write_vault_note，绕过 ①）
#   ③ execute_command（core/gateway/security.py 的 _SYS_ESCAPE_PATTERNS 不含 /mnt，不拦）
# 只在一条上加规矩必漏另两条 → 判据放在工具执行的统一入口 _run_item。
# 2026-09-28(成对改): 路径指纹改引**唯一真源** core.lib.paths.vault_markers()
# （此前本文件写死三个串 ⇒ 脑根一改，本条判据在场却打错对象）。同名常量保留 = 兼容既有断言。
from core.lib.paths import contains_vault_marker, vault_markers

_VAULT_MARKERS = vault_markers()
_OBS_WRITE_ACTIONS = ("write_note", "update_sop", "append_pitfall", "write_draft", "update_draft")
_WRITE_SIGNALS = (">>", ">", "tee ", "cp ", "mv ", "rm ", "mkdir ", "touch ", "truncate ", "sed -i", "dd ", "open(")


def _is_vault_write(tool, args):
    """统一判据。契约：返回 (是否vault写, 命中通道名)。"""
    t = str(tool or "")
    a = args or {}
    if t == "obsidian_knowledge":
        if str(a.get("action") or "") in _OBS_WRITE_ACTIONS:
            return True, "obsidian_knowledge"
    if t == "cu_learning":
        # 收紧（2026-09-13）：原先用子串 "sop" 匹配整个参数 blob → **list_sops 这类读动作被误判成写**
        # （fault 测试当场抓到）。改为按 action 精确匹配 + 写入形态（sop_key + content）兜底。
        _act = str(a.get("action") or "").lower()
        if _act in ("persist_sop", "write_sop", "save_sop", "update_sop", "upsert_sop"):
            return True, "cu_learning.persist_sop"
        if "sop_key" in a and any(k in a for k in ("content", "text", "body")):
            return True, "cu_learning.persist_sop"
    if t in ("execute_command", "run_command", "shell"):
        _cmd = str(a.get("command") or "")
        # 保守兜底「Obsidian」字面**保留**（只可收紧不可放宽）：命令串出现该词即按 vault 写
        # 处理，比精确判据宽 —— 宁可多拦。⛔ 不得据此省掉 contains_vault_marker()。
        if not (contains_vault_marker(_cmd) or "Obsidian" in _cmd):
            return False, ""
        # 收紧（2026-09-13，修我自己的误伤）：此前只要命令串里出现 vault 路径就判写 ->
        # grep/cat/ls 这类读也被当成写，续跑期 PA 连读 vault 自证都做不了。
        # 现在要求「路径命中」且「有写意图」同时成立；用结构化信号，不做纯子串匹配。
        _low = _cmd.lower()
        if any(_sig in _low for _sig in _WRITE_SIGNALS):
            return True, "execute_command"
        return False, ""
    return False, ""


def _run_pre_phase(*, btool_calls, bmsg, messages, session_id, user_id, bridge_round, ea_seen):
    """S6-D1 pre-guard：assistant_message 事件溯源 + 空参拦截 + run_pre_guards + write_pending 收集。

    契约：原地改 messages（append _bassist / 空参 steer 兜底）与 ea_seen（计数）；
    返回 (pre_items, pre_terminal, pre_wp_list)。write_pending/plan_pending/escalation_blocked 由 pre_terminal 承载。
    """
    import json

    from core.gateway.write_gate import _get_pending_lock, _pending_writes, _persist_pending_writes, _plan_pending
    from core.lib.gateway_helpers import _get_sandbox_base

    # 服务端真实执行工具（回传 assistant tool_calls + reasoning_content）
    _bassist = {"role": "assistant", "content": bmsg.get("content", ""), "tool_calls": btool_calls}
    # 2026-09-06 修复: tool_calls assistant 必须带 reasoning_content 键(值可空串),
    # derive 异常回退内存 messages 直发时缺键 → DeepSeek 400(与 execute_agent_task 同构修复)。
    _bassist["reasoning_content"] = bmsg.get("reasoning_content")
    messages.append(_bassist)
    # P2a 事件溯源双写: assistant_message
    try:
        from core.gateway.session_log import log_event

        log_event(
            session_id,
            "assistant_message",
            {
                "content": bmsg.get("content", ""),
                "tool_calls": btool_calls,
                "reasoning_content": bmsg.get("reasoning_content")
                if isinstance(bmsg.get("reasoning_content"), str)
                else "",
            },
            turn_id=bridge_round,
            step_id=0,
        )
    except Exception:
        pass
    # ===== P3: 工具执行池化(串行 pre-guard → 并行读/串行写 → 按序提交) =====
    from core.gateway.guards.runner import run_pre_guards

    # 阶段1: 逐个 run_pre_guards(串行, 与现状一致); 命中终止守卫即停。
    # R3(2026-08-30): write_pending 收集同批所有写请求(批量审批卡), 不再第一个就 break;
    # plan_pending/escalation_blocked 仍是单点终止(不批量)。
    _pre_items = []
    _pre_terminal = None
    _pre_wp_list = []  # R3: 同批 write_pending 列表(批量审批)
    for _btc in btool_calls:
        _bfn = _btc.get("function", {}).get("name", "")
        if not _bfn:
            # 工具名为空 → 跳过，不执行不 append（防「未知工具」污染 messages）
            continue
        try:
            _bargs = json.loads(_btc["function"]["arguments"])
        except Exception:
            _bargs = {}
        # S3 空参单点(shared_state.empty_arg_error): 缺必填参数 → 直接 deny 收集(不触发审批卡)
        from core.gateway.shared_state import empty_arg_error as _v9_empty_arg_error

        _l5e = _v9_empty_arg_error(_bfn, _bargs)
        # (2026-09-07 write_file reason 强制): 审批卡必须带真实写理由 —
        # 缺 reason 放行进审批卡 → 人工审核看不到理由(实证两次缺 reason)。
        # 在桥接 agent 路径拦截并让模型补 reason 重试(守卫层保持宽容, 不波及非 agent 写入)。
        if _bfn == "write_file" and not _l5e:
            if not str((_bargs or {}).get("reason") or "").strip():
                _l5e = "write_file 缺少必填参数 reason(空参调用, 直接拦截, 不触发审批) — " "请说明写该文件的理由(写给谁/为什么/影响范围), 补上后重试"
        # (2026-09-08 空 path 引导增强): 拦截消息补「如何补参」具体示例 —
        # 只报「缺 path」不教怎么补 → Agent 反复空参重试(实证 8 次)。
        if _l5e and _bfn == "write_file" and "缺少必填参数 path" in _l5e:
            _l5e = (
                _l5e + "；补参示例: write_file(path='data/reports/<你的目标文件名>.md', "
                "content='<要写入的完整内容>', reason='<写给谁/为什么>'); "
                "path 应从任务目标与已调研内容推导(报告类 data/reports/, 临时 data/tmp/, 不要空参重试)"
            )
        if _l5e:
            _pre_items.append(
                {
                    "idx": len(_pre_items),
                    "btc": _btc,
                    "bfn": _bfn,
                    "bargs": _bargs,
                    "gdeny": {"status": "param_error", "reason": _l5e},
                }
            )
            print(f"[L5_EMPTY_ARG] {_l5e}")
            # (2026-09-05 封面任务 obsidian 空参循环): 同工具空参连续 ≥2 次 → 注入格式引导,
            # 打断"模型反复发空参 tool_calls"的 arg 生成故障(此前 8 次空 obsidian_knowledge() 才空回复)
            _ea_key = (_bfn, session_id)
            _ea_cnt = ea_seen.get(_ea_key, 0) + 1
            ea_seen[_ea_key] = _ea_cnt
            if _ea_cnt == 2:
                _fmt_hint = (
                    "[系统] 你连续以空参数/缺必填参数调用 " + _bfn + "。请检查 tool_calls 的 arguments 是否完整。"
                    "例如 obsidian_knowledge 需 action=read/search/write_note/... (及对应参数如 sop_key/folder/content); "
                    "write_file 需 path+content; execute_command 需 command; "
                    "fetch_web/browse_web 需 url=https://...(仅 url, 无 action); playwright_browser/browser_local 需 action。"
                    "修正后重试, 不要重复空参调用。"
                )
                if _bfn == "write_file":
                    _fmt_hint = (
                        "[系统] 你已连续 2 次以空参数调用 write_file。补参格式: "
                        "write_file(path='data/reports/xxx.md', content='...', reason='...')。"
                        "path 来自你的任务目标与已调研内容(PPT/报告类 → data/reports/ 或沙箱内路径), "
                        "不要空参重试; 若不确定 path 先用 list_dir 确认目录。"
                    )
                # 2026-09-08: 空参 steer 必须走 add_steer 通道 —
                # 本地 messages.append 会被下轮 derive 重建抹掉(steer 从未送达模型,
                # 实证 8 次空 write_file 仍在继续)。add_steer 在每轮 derive 后 drain 注入。
                from core.gateway.shared_state import add_steer as _ea_steer

                try:
                    _ea_steer(session_id, _fmt_hint)
                except Exception:
                    messages.append({"role": "system", "content": _fmt_hint})
            elif _ea_cnt == 4:
                _ea4 = (
                    "[系统] 你已连续 4 次空参/缺参调用 " + _bfn + "，禁止再次空参调用。"
                    "若无法确定参数(如 write_file 的 path)，请基于任务目标补一个沙箱内路径并带 reason 执行；"
                    "若确实无法完成请输出明确说明, 不要继续空参。"
                )
                from core.gateway.shared_state import add_steer as _ea_steer4

                try:
                    _ea_steer4(session_id, _ea4)
                except Exception:
                    messages.append({"role": "system", "content": _ea4})
            continue
        # 已确认：清除 approved 标记，放行执行（#106 C5 锁内, 保留原语义 — 仅写工具）
        if _bfn in ("write_file", "write_large", "edit_file"):
            with _get_pending_lock():
                _pending_writes.pop(session_id, None)
                _persist_pending_writes(user_id, session_id)  # #106 清除持久化
        # P1 S6: 统一 guard 入口(全局含审批) — pre 检测(串行, 行为一致)
        _gdeny = run_pre_guards(
            {
                "tool": _bfn,
                "args": _bargs,
                "user_id": user_id,
                "session_id": session_id,
                "sandbox_base": str(_get_sandbox_base(user_id, session_id)),
                "messages": messages,
                "tool_call_id": _btc.get("id", ""),
                # 修复: approved 应传计划审批状态(_plan_pending) — 之前误传写审批(_pending_writes),
                # PlanGuard 永远看不到 approved=True → 确认后仍触发计划卡 → 死循环
                "approved": _plan_pending.get(session_id, {}),
                "tool_calls_plan": btool_calls,
                "assistant_content": str(bmsg.get("content", ""))[:1500],
            }
        )
        if _gdeny is not None:
            _gst = _gdeny.get("status", "default")
            if _gst == "write_pending":
                # R3: 收集所有写请求(批量卡); 记录原始 tool_call 供确认后执行
                _wp_pw = _gdeny.get("pending_write") or {}
                _wp_pw["_btc"] = _btc
                _wp_pw["_bargs"] = _bargs
                _wp_pw["_bfn"] = _bfn
                _pre_wp_list.append(_wp_pw)
                _pre_items.append({"idx": len(_pre_items), "btc": _btc, "bfn": _bfn, "bargs": _bargs, "gdeny": _gdeny})
                continue  # 继续收集同批其它写请求
            if _gst in ("plan_pending", "escalation_blocked"):
                _pre_terminal = (_gst, _gdeny, _bfn, _bargs, _btc)
                break
        _pre_items.append({"idx": len(_pre_items), "btc": _btc, "bfn": _bfn, "bargs": _bargs, "gdeny": _gdeny})
    # R3: 有 write_pending 收集 → 设终止(优先批量)
    if _pre_wp_list:
        _pre_terminal = ("write_pending", None, None, None, None)
    return _pre_items, _pre_terminal, _pre_wp_list


def _v9_split_pool(pre_items, exclusive):
    """P3: 工具池分组 — 非 exclusive 且未 deny → 并行组(ThreadPool); denied/exclusive → 串行组(保序 barrier)。

    pre_items: [{idx, btc, bfn, bargs, gdeny}] 已过串行 pre-guard 的工具
    exclusive: 串行工具集合(write_file/write_large/edit_file/execute_command)
    返回 (parallel_items, serial_items)
    """
    _par = [it for it in pre_items if it["gdeny"] is None and it["bfn"] not in exclusive]
    _ser = [it for it in pre_items if it["gdeny"] is not None or it["bfn"] in exclusive]
    return _par, _ser


def _run_exec_phase(*, pre_items, session_id, user_id, exec_tool_fn):
    """S6-D2 执行：并行读/串行写 pool（_v9_split_pool 分组 + ThreadPool 并行读 + 串行写 barrier）。

    契约：返回 (exec_results, cancelled)。cancelled=True 时调用方 break（协作取消）。
    """
    from core.gateway.shared_state import is_cancel_requested

    # 阶段2: 执行 — 非 exclusive 读工具 ThreadPool 并行; exclusive 写/命令串行 barrier; denied 直接收集 deny 结果
    try:
        from core.gateway.shared_state import _load_v9_execution_policy

        _eb3 = (_load_v9_execution_policy() or {}).get("execution_budget", {}) or {}
        _max_parallel = int(_eb3.get("max_parallel_tools", 4) or 0)
        _excl3 = set(_eb3.get("exclusive_tools", ["write_file", "write_large", "edit_file", "execute_command"]))
    except Exception:
        _max_parallel = 4
        _excl3 = {"write_file", "write_large", "edit_file", "execute_command"}

    def _run_item(_it):
        if _it["gdeny"] is not None:
            return {"success": False, "error": _it["gdeny"].get("reason", "工具调用被拒绝"), "guard_denied": True}
        # 续跑期间禁写 vault（统一守卫）：一次核验误判若不拦，会把误判放大成知识库污染
        try:
            from core.gateway.shared_state import is_continuation as _is_cont

            if _is_cont(session_id):
                _vw, _ch = _is_vault_write(_it["bfn"], _it["bargs"])
                if _vw:
                    print(f"[CONTINUATION_GUARD] 续跑期间拦截 vault 写(channel={_ch}) session={session_id}")
                    return {
                        "success": False,
                        "continuation_blocked": True,
                        "channel": _ch,
                        "error": ("续跑期间禁止写 vault（防一次误判污染知识库，channel=%s）。" "请先修正被判失败的产物，或改写沙箱路径 data/reports/。") % _ch,
                    }
        except Exception as _e_cg:
            print(f"[CONTINUATION_GUARD] 判据异常(放行): {_e_cg}")
        # S3 统一执行缓存(shared_state.tool_exec_cache): 读类同参且上次成功 → 不重复执行
        from core.gateway.shared_state import tool_exec_cache_get as _l4_cache_get
        from core.gateway.shared_state import tool_exec_cache_put as _l4_cache_put

        _l4_cached = _l4_cache_get(session_id, _it["bfn"], _it["bargs"], with_meta=True)
        if _l4_cached is not None:
            _c4 = dict(_l4_cached)
            _c4["l4_cached"] = True
            # 2026-09-13: 带上快照时点 —— 调用方据此判断"这是不是旧快照",
            # 修 bug #6 的次生伤害(agent 拿到旧快照却无法自知, 只好不冒充核验通过)。
            if _c4.get("_cached_at"):
                _c4["cached_at"] = _c4["_cached_at"]
                _c4.setdefault("cached_hint", "这是 %s 的缓存快照; 若你刚写过该文件, 请用不同参数重读或改走其它读取方式。" % _c4["_cached_at"])
            print(f"[L4_DEDUP] {_it['bfn']} 同参命中缓存({_c4.get('cached_at') or '?'}), 跳过执行")
            return _c4
        _res4 = exec_tool_fn(_it["bfn"], _it["bargs"], user_id, session_id)
        _l4_cache_put(session_id, _it["bfn"], _it["bargs"], _res4)
        return _res4

    # #1 协作取消: 并行池执行前检查(并行中的工具自然跑完, 不硬杀)
    if is_cancel_requested(session_id):
        print(f"[CANCEL] 并行池执行前取消, 退出 session={session_id}")
        return {}, True
    _exec_results = {}
    _par_items, _ser_items = _v9_split_pool(pre_items, _excl3)
    print(f"[P3_POOL] 并行组 {len(_par_items)} 工具, 串行组 {len(_ser_items)} (max_parallel={_max_parallel})")
    if _par_items and _max_parallel > 0:
        from concurrent.futures import ThreadPoolExecutor as _TPE3

        with _TPE3(max_workers=min(_max_parallel, len(_par_items))) as _ex3:
            _futs3 = {_ex3.submit(_run_item, _it): _it["idx"] for _it in _par_items}
            for _f3 in _futs3:
                _exec_results[_futs3[_f3]] = _f3.result()
    for _it in _ser_items:  # 串行: denied 结果 + exclusive 写/命令(同一时刻最多 1 个)
        _exec_results[_it["idx"]] = _run_item(_it)
    return _exec_results, False


def _commit_results(
    *,
    pre_items,
    exec_results,
    messages,
    bmsg,
    session_id,
    user_id,
    bridge_round,
    turn_id,
    tokens,
    tool_steps,
    bridge_exhausted,
    is_7b_fallback,
    runtime,
    write_turn_end_fn,
    truncate_fn,
):
    """S6-D3 结果提交：按模型调用顺序双写(事件溯源/读去重/探索止损/重复读止损) + run_post_guards + 熔断(drift/browser/envblock/DOM/同域)。

    契约：原地改 messages（append tool 结果）与 bmsg（止损提示）与 tool_steps 与 runtime（动态计数）；
    返回决策 dict {sevenb_fail, bridge_exhausted}。sevenb_fail=True 时调用方 build return。
    """
    import json
    import time

    from core.gateway.guards.runner import run_post_guards

    # 阶段3: 按模型调用顺序提交(双写 + messages + post guard 串行, 保 messages 顺序稳定)
    for _it in pre_items:
        _bfn = _it["bfn"]
        _bargs = _it["bargs"]
        _btc = _it["btc"]
        _btr = exec_results[_it["idx"]]
        if is_7b_fallback and not _btr.get("success"):
            runtime["_7b_fail_streak"] = runtime.get("_7b_fail_streak", 0) + 1
            print(f"[7B_FAIL] 连续失败 {runtime['_7b_fail_streak']}/3")
            if runtime["_7b_fail_streak"] >= 3:
                write_turn_end_fn(session_id, turn_id, tokens, "error", "7B 连续失败 3 次，停止降级", len(tool_steps))
                return {"sevenb_fail": True, "bridge_exhausted": bridge_exhausted}
        elif is_7b_fallback and _btr.get("success"):
            runtime["_7b_fail_streak"] = 0
            runtime["_7b_last_result"] = json.dumps(_btr, ensure_ascii=False, default=str)[:1500]
        # P2a 事件溯源双写: tool_call
        try:
            from core.gateway.session_log import log_event

            log_event(
                session_id,
                "tool_call",
                {"name": _bfn, "arguments": _bargs, "call_id": _btc.get("id", "")},
                turn_id=bridge_round,
                step_id=0,
            )
        except Exception:
            pass
        # P2a 事件溯源双写: tool_result
        try:
            from core.gateway.session_log import log_event

            _btr_content = json.dumps(_btr, ensure_ascii=False, default=str)
            log_event(
                session_id,
                "tool_result",
                {
                    "name": _bfn,
                    "call_id": _btc.get("id", ""),
                    "content": truncate_fn(_btr_content),
                    "success": bool(_btr.get("success")) if isinstance(_btr, dict) else False,
                },
                turn_id=bridge_round,
                step_id=0,
            )
        except Exception as _log_err:
            print(f"[TOOL_RESULT_LOG_FAIL] {_log_err}")
        print(f"[APPEND_DEBUG] _bfn={_bfn} _btr={str(_btr)[:150]}")
        # R2 补漏(2026-08-30 架构根治): execute_command 读文件去重 —
        # Agent 用 python3 -c 'open(...).read()' / cat 文件 绕过 read_file 缓存, 同一文件反复读
        # 全量注入上下文 → 上下文膨胀 + token 爆炸。检测"纯读文件"命令: 提取路径+内容 hash,
        # 与 _read_content_cache(session 级)比对, 同内容 → 替换为短提示(不再重复注入全文)。
        if _bfn == "execute_command" and isinstance(_btr, dict) and _btr.get("success"):
            try:
                import hashlib as _hl3
                import re as _re3

                _cmd3 = str(_bargs.get("command") or "")
                _is_read_cmd = bool(
                    _re3.search(
                        r"python3?\s+-c\b[\s\S]*(?:open\([^)]*\)|read_text|readlines\(|\.read\(|cat\s+[\w./-]+)", _cmd3
                    )
                    or _re3.search(r"^cat\s+[\w./-]+", _cmd3.strip())
                )
                if _is_read_cmd:
                    # 提取被读文件路径(优先 open() 内引号, 其次 cat 后)
                    _m3 = _re3.search(r"open\(\s*['\"]([^'\"]+)['\"]", _cmd3)
                    if not _m3:
                        _m3 = _re3.search(r"cat\s+([\w./-]+)", _cmd3)
                    if _m3:
                        _rp3 = _m3.group(1)
                        _stdout3 = str(_btr.get("stdout") or "")
                        if _stdout3:
                            _h3 = _hl3.md5(_stdout3.encode("utf-8", "ignore")).hexdigest()
                            from core.gateway.shared_state import _read_content_cache as _rc3

                            _sess3 = _rc3.setdefault(session_id, {})
                            _rk3 = f"r2:{_rp3}"
                            if _sess3.get(_rk3) == _h3:
                                _btr = dict(_btr)
                                _btr["stdout"] = f"[已读缓存] {_rp3} 内容与上次读取一致({len(_stdout3)} 字符)。请直接基于已读取内容推进，不要重复读取。"
                                _btr["r2_cached"] = True
                                print(f"[R2_EXEC_READ_DEDUP] {_rp3} 内容未变, 去重注入")
                            else:
                                _sess3[_rk3] = _h3
            except Exception:
                pass
        # ④⑤(2026-09-11): 读全 — read_file(沙箱)+obsidian_knowledge(vault) 提高截断上限, 让 PA 读完整文件(拼全篇); 其余保持 2000 防上下文膨胀
        _trunc_limit = 12000 if _bfn in ("read_file", "obsidian_knowledge") else 2000
        messages.append(
            {
                "role": "tool",
                "tool_call_id": _btc.get("id", ""),
                "content": truncate_fn(_btr_content, limit=_trunc_limit),
            }
        )
        # 探索止损(上下文爆炸修复): 连续 5 次 list_dir/read_file/search_files 无实质产出
        # → 注入「停止探索, 明确任务」提示, 打断「迷失→更多探索→爆炸」循环
        try:
            _EXPLORE_THRESHOLD = 5
            _EXPLORE_TOOLS = ("list_dir", "read_file", "search_files", "query_index")
            if _bfn in _EXPLORE_TOOLS:
                _explore_key = f"explore_{session_id}_{turn_id}"
                _explore_cnt = runtime.get(_explore_key, 0)
                _out_len = len(str(_btr.get("content") or _btr.get("stdout") or ""))
                _out_success = bool(_btr.get("success"))
                if _out_success and _out_len < 100:
                    _explore_cnt += 1
                    runtime[_explore_key] = _explore_cnt
                    if _explore_cnt >= _EXPLORE_THRESHOLD:
                        _hint = f"[系统] 已连续 {_explore_cnt} 次 {_bfn} 无实质产出。" f"请停止探索目录，明确当前任务目标并直接执行，不要再翻查无关文件。"
                        bmsg["content"] = (bmsg.get("content") or "") + chr(10) + chr(10) + _hint
                        print(f"[EXPLORE_STOP] {session_id} 连续 {_explore_cnt} 次无产出探索, 已注入止损提示并终止本轮")
                        runtime[_explore_key] = 0
                        # 止损收敛: 终止本轮(不再续跑), 防「探索到死」循环 — 目标由完成判定或下一轮用户新任务接管
                        bridge_exhausted = True
                        break
                else:
                    runtime[_explore_key] = 0  # 有产出/失败 → 重置计数
            # 重复读同一文件止损(2026-08-29): read_file 同一路径连续 3 次(即使有产出)
            # → 提示收敛(低效循环: 同一文件反复读, 浪费工具预算不推进任务)
            if _bfn in ("read_file", "list_dir", "search_files"):
                _dup_path = str(_bargs.get("path") or "")[:120]
                if _dup_path:
                    # B4(2026-08-30): 跨轮重复读去重 — 计数改 session 级(不按 turn 重置)
                    # 2026-08-30 v3 修复: objective/goal_id 作重置键都不可靠 —
                    # 每个用户消息都新建 goal(目标隔离), objective 前 60 字符各异
                    # (如"继续"、"清理5005"、带时间戳措辞) → 每次消息误清空 → 跨轮失效。
                    # 改按 时间窗(3 分钟内)累计: 短时间反复读同一文件 → 拦截; 隔久自然重置。
                    _dup_key = f"dupread_{session_id}"
                    _dup_hist = runtime.get(_dup_key, {})
                    _now_dup = time.time()
                    _dup_hist = {p: c for p, c in _dup_hist.items() if c.get("ts", 0) > _now_dup - 180}  # 3 分钟窗
                    _dup_hist[_dup_path] = {"n": _dup_hist.get(_dup_path, {}).get("n", 0) + 1, "ts": _now_dup}
                    runtime[_dup_key] = _dup_hist
                    if _dup_hist[_dup_path]["n"] >= 3:
                        _hint2 = (
                            f"[系统] 已连续 {_dup_hist[_dup_path]['n']} 次读取同一路径 {_dup_path}。" f"请停止重复读取，基于已获取内容直接执行或输出结论。"
                        )
                        bmsg["content"] = (bmsg.get("content") or "") + chr(10) + chr(10) + _hint2
                        print(f"[DUP_READ_STOP] {session_id} 重复读 {_dup_path} x{_dup_hist[_dup_path]['n']}, 已提示收敛")
                        runtime[_dup_key] = {}
                        bridge_exhausted = True
                        break
        except Exception:
            pass
        # P1 S6: 统一 guard 入口 — post 观察(reminder/审计/失败计数); P0-2 消费返回值
        _gres = run_post_guards(
            {
                "tool": _bfn,
                "args": _bargs,
                "user_id": user_id,
                "session_id": session_id,
                "result": _btr,
                "agent_id": session_id,
            }
        )
        # P0-2: 消费 guard_results — 连续失败提示注入 / 暂停终止
        if _gres:
            if _gres.get("paused"):
                print(f"[GUARD_PAUSE] {_gres.get('error', '连续失败暂停')}")
                bmsg["content"] = (
                    (bmsg.get("content") or "") + chr(10) + chr(10) + "[系统] " + str(_gres.get("error", "连续失败，任务已暂停"))
                )
                _guard_paused = True
                bridge_exhausted = True
                break
            _inj_msg = _gres.get("inject_message")
            if _inj_msg:
                # P4 steer 全量迁移: guard_results.inject_message 走 steer 通道(下一轮消费),
                # 不再直接拼 content(与 tool_router 的 add_steer 合并为单一通道, 防双份注入)
                print(f"[GUARD_INJECT→STEER] {_inj_msg}")
                try:
                    from core.gateway.shared_state import add_steer

                    add_steer(session_id, str(_inj_msg))
                except Exception:
                    bmsg["content"] = (bmsg.get("content") or "") + chr(10) + chr(10) + "[系统] " + str(_inj_msg)
        print(f"[V9_BRIDGE] 执行工具 {_bfn} → success={_btr.get('success', False)} btr={str(_btr)[:200]}")
        # #101 收集工具步骤摘要（前端渲染工具使用记录）
        _step_arg = str(_bargs.get("path") or _bargs.get("command") or "")[:120]
        _step_ok = bool(_btr.get("success"))
        _step_err = str(_btr.get("error") or "")[:120] if not _step_ok else ""
        # max_tokens 空产出修复: 成功步骤携带结果摘要(供 _buildtool_steps_summary 提取, 不调 LLM)
        _step_result = ""
        if _step_ok and isinstance(_btr, dict):
            _step_result = str(_btr.get("content") or _btr.get("stdout") or _btr.get("output") or "")[:160].strip()
        # 截图流可视化: playwright_browser 截图成功 → tool_step 挂截图字段(前端渲染缩略图)
        _step_shot = {}
        if _step_ok and isinstance(_btr, dict):
            _su = _btr.get("screenshot_url")
            _sp = _btr.get("screenshot_path")
            if _su or _sp:
                _step_shot = {"screenshot_url": str(_su or ""), "screenshot_path": str(_sp or "")}
        tool_steps.append(
            {
                "tool": _bfn,
                "arg": _step_arg,
                "success": _step_ok,
                "error": _step_err,
                "round": bridge_round,
                "result": _step_result,
                **_step_shot,
            }
        )
        # R2 修复(2026-08-30): 任务漂移检测 — 连续 8 次"调试脚本类"调用(写 data/tmp/或 python -c)
        # 无实质产出 → 注入换路提示(Agent 曾深挖解码 Google URL 写 30+ 脚本, 5 轮迷失)
        try:
            _is_debug_call = str(_bargs.get("path") or "").startswith("data/tmp/") or "data/tmp/" in str(
                _bargs.get("command") or ""
            )
            _drift_key = f"drift_{session_id}_{turn_id}"
            _drift_cnt = runtime.get(_drift_key, 0)
            if _is_debug_call:
                _drift_cnt += 1
                runtime[_drift_key] = _drift_cnt
                if _drift_cnt >= 8:
                    _drift_hint = (
                        "[系统] 已连续 8 次写临时调试脚本(data/tmp/)。"
                        "请评估当前方向：若在死胡同（如逆向解码/过度工程），"
                        "换更直接的方式（如 browse_web/fetch_web 直接访问原文/页面），"
                        "不要继续堆调试脚本。"
                    )
                    bmsg["content"] = (bmsg.get("content") or "") + chr(10) + chr(10) + _drift_hint
                    print(f"[DRIFT_STOP] {session_id} 连续 {_drift_cnt} 次调试脚本调用, 已提示换路")
                    runtime[_drift_key] = 0
            else:
                runtime[_drift_key] = 0  # 非调试调用 → 重置
        except Exception:
            pass
        # (2026-09-07 浏览器不可用熔断): browser_local/playwright_browser/browser_hybrid 连续 2 次
        # 「浏览器实例不可用(browser has been closed)」→ 注入换路提示(此前 Agent 反复重试 5+ 次烧步数)。
        # 环境问题重试无益: 提示改用 fetch_web/browse_web/web_search 或报告阻塞等待客户端启动。
        try:
            if _bfn in ("browser_local", "playwright_browser", "browser_hybrid"):
                from core.gateway.shared_state import browser_unavailable_error as _buv_err

                _buv = _buv_err(_btr)
                _buv_key = "buv_" + str(session_id) + "_" + str(turn_id)
                _buv_cnt = runtime.get(_buv_key, 0)
                if _buv:
                    _buv_cnt += 1
                    runtime[_buv_key] = _buv_cnt
                    if _buv_cnt == 2:
                        _buv_hint = (
                            "[系统] 浏览器实例不可用(" + str(_buv)[:80] + ")。禁止继续调用 browser_local/playwright_browser。"
                            "请改用 fetch_web/browse_web/web_search 获取公开网页内容, 或输出阻塞报告等待浏览器客户端启动。"
                        )
                        from core.gateway.shared_state import add_steer as _st_buv

                        try:
                            _st_buv(session_id, _buv_hint)
                        except Exception:
                            bmsg["content"] = (bmsg.get("content") or "") + chr(10) + chr(10) + _buv_hint
                        print("[BROWSER_UNAVAIL_STOP] %s 连续 %d 次浏览器不可用, 已提示换路" % (session_id, _buv_cnt))
                else:
                    runtime[_buv_key] = 0  # 浏览器调用成功/其它错误 → 重置计数
        except Exception:
            pass
        # (2026-09-07 EnvBlockGuard): 通用环境阻塞收敛 — 浏览器/抓取/表格类工具返回
        # 「登录墙/0行/302无限重定向/加载中/浏览器不可用」属环境阻塞, 换法硬闯无益
        # (逐格读 canvas/反复 extract/换抓取工具实证烧预算)。同一任务累计 ≥3 次 →
        # 注入硬收敛: 停止硬闯, 已获内容即落盘, 否则输出阻塞报告请老板(登录态/CSV/截图),
        # 登录态可用时用 table_extract 一次读取。
        try:
            if _bfn in (
                "browser_local",
                "playwright_browser",
                "browser_hybrid",
                "fetch_web",
                "browse_web",
                "table_extract",
            ):
                from core.gateway.shared_state import env_block_error as _envb_err

                _envb = _envb_err(_btr)
                _envb_key = "envb_" + str(session_id) + "_" + str(turn_id)
                _envb_cnt = runtime.get(_envb_key, 0)
                if _envb:
                    _envb_cnt += 1
                    runtime[_envb_key] = _envb_cnt
                    bmsg_cur = str(bmsg.get("content") or "")
                    if _envb_cnt == 3 and "环境阻塞" not in bmsg_cur:
                        _envb_hint = (
                            "[系统] 本任务连续 %d 次遇到环境阻塞(%s)。禁止继续用替代方式硬闯"
                            "(逐格读 canvas / 反复 extract 页面 / 反复换抓取工具)。"
                            + chr(10)
                            + "请: 1) 若已获取目标内容 → 立即落盘(write_note/write_draft);"
                            + chr(10)
                            + "2) 否则输出阻塞报告, 请老板提供: 已登录飞书会话 / 导出 CSV / 截图;"
                            + chr(10)
                            + "3) 登录态可用时用 table_extract 一次读取整表。"
                        ) % (_envb_cnt, str(_envb)[:80])
                        from core.gateway.shared_state import add_steer as _st_envb

                        try:
                            _st_envb(session_id, _envb_hint)
                        except Exception:
                            bmsg["content"] = bmsg_cur + chr(10) + chr(10) + _envb_hint
                        print("[ENVBLOCK_STOP] %s 连续 %d 次环境阻塞(%s), 已提示停止硬闯" % (session_id, _envb_cnt, str(_envb)[:60]))
                else:
                    runtime[_envb_key] = 0
        except Exception:
            pass
        # (2026-09-07 DOM 深挖上限): browser_local evaluate/extract/scroll 同任务 ≥16 次
        # → 注入停止深挖(防 canvas 逐格/反复 extract 等读法烧预算; 深挖应换 table_extract/截图)。
        try:
            if _bfn == "browser_local":
                _bl_act = str((_bargs or {}).get("action") or "")
                if _bl_act in ("evaluate", "extract", "scroll"):
                    _dig_key = "dig_" + str(session_id) + "_" + str(turn_id)
                    _dig_cnt = runtime.get(_dig_key, 0) + 1
                    runtime[_dig_key] = _dig_cnt
                    bmsg_cur2 = str(bmsg.get("content") or "")
                    if _dig_cnt == 16 and "DOM 深挖" not in bmsg_cur2:
                        _dig_hint = (
                            "[系统] 已连续 %d 次 browser_local %s 调用, 疑似深挖页面 DOM/网格。"
                            + chr(10)
                            + "停止逐格/逐元素提取: 整表用 table_extract 一次读取, 需要看画面用 screenshot, "
                            + "拿不到就报告内容缺口(请老板导出/截图), 不要继续逐格读取。"
                        ) % (_dig_cnt, _bl_act)
                        from core.gateway.shared_state import add_steer as _st_dig

                        try:
                            _st_dig(session_id, _dig_hint)
                        except Exception:
                            bmsg["content"] = bmsg_cur2 + chr(10) + chr(10) + _dig_hint
                        print("[DOM_DIG_STOP] %s %s 已 %d 次, 提示停止深挖" % (session_id, _bl_act, _dig_cnt))
        except Exception:
            pass
        # (2026-09-09 同域熔断): 网络工具连续失败 — 同 (session, tool, domain) ≥2 次换源, ≥3 次停该域(标待线下核实)。
        # 治 bing/sm.cn/browser 重复重试每轮烧预算(与 browser 熔断/EnvBlock 互补, 专治同域硬刚)。
        try:
            _df_tools = ("fetch_web", "browse_web", "browser_local", "playwright_browser", "table_extract")
            if _bfn in _df_tools and not (_btr or {}).get("success"):
                import re as _re_df

                _err_df = str((_btr or {}).get("error") or "")
                _url_df = str((_bargs or {}).get("url") or "")
                _m_df = _re_df.search(r'https?://([^/\s"]+)', _err_df) or _re_df.search(r'https?://([^/\s"]+)', _url_df)
                _dom_df = (_m_df.group(1) if _m_df else (_bfn + ":<unknown>"))[:80].lower()
                _df_key = "domfail_" + str(session_id) + "_" + str(turn_id) + "_" + _bfn + "_" + str(_dom_df)
                _df_cnt = runtime.get(_df_key, 0) + 1
                runtime[_df_key] = _df_cnt
                if _df_cnt == 2:
                    _df_hint = (
                        "[系统] 访问 " + str(_dom_df) + " 已连续失败 2 次(" + str(_err_df)[:100] + ")。"
                        "停止重试该域: 换权威媒体/政务公众号/搜索摘要等替代来源, 不要再次访问同一域。"
                    )
                    from core.gateway.shared_state import add_steer as _st_df

                    try:
                        _st_df(session_id, _df_hint)
                    except Exception:
                        pass
                    print("[DOMFAIL_STOP] %s %s x%d 换源提示" % (session_id, _dom_df, _df_cnt))
                elif _df_cnt >= 3:
                    _df_hint2 = (
                        "[系统] 访问 " + str(_dom_df) + " 已连续失败 " + str(_df_cnt) + " 次, 该域本轮停止访问。"
                        "对应政策项标注「待线下核实」, 禁止再对同一域发起任何请求。"
                    )
                    from core.gateway.shared_state import add_steer as _st_df2

                    try:
                        _st_df2(session_id, _df_hint2)
                    except Exception:
                        pass
                    print("[DOMFAIL_HARD] %s %s x%d 停域" % (session_id, _dom_df, _df_cnt))
            else:
                # 成功/非网络工具 → 无需处理(失败计数按域自然衰减由 turn 隔离)
                pass
        except Exception:
            pass
    return {"sevenb_fail": False, "bridge_exhausted": bridge_exhausted}


def _pending_card_view(_pw):
    """M2-A · Step 3.3（方案 A）：审批卡的**响应视图** —— 只读叠加，不改 `_pending_writes` 结构、
    不进 `_persist_pending_writes` 白名单 ⇒ **不污染 `.agent_state.json`**（在响应组装时现算）。

    两条纪律（设计稿 §2.1；前端有静态反例钉死「不得本地算时间」）：
    ① 剩余秒数**只能后端算**（`expires_in_s`，来源 `write_gate._PENDING_TTL`，不写死数值）；
    ② **未知即未知**：取不到就是 `None`，**不兜底成 0**（0 会被读成「已过期」⇒ 假拒绝）。
    `revoke_window` 透传 `HoldQueue.visibility()`；写审批**未接 hold**（产品侧 0 调用点）⇒
    今天恒 `{"show": False}`，前端只在 `show=True` 时渲染（不暗示一个不存在的窗口）。
    """
    _view = dict(_pw or {})
    try:
        import time as _t_pcv

        _ts = float(_view.get("ts") or 0)
        if _ts <= 0:
            _view["expires_in_s"] = None
        else:
            from core.gateway.write_gate import _PENDING_TTL as _TTL_pcv

            _view["expires_in_s"] = max(0, int(_TTL_pcv - (_t_pcv.time() - _ts)))
    except Exception:
        _view["expires_in_s"] = None
    try:
        from core.pes.authorization import HoldQueue as _HQ_pcv

        _vw = _HQ_pcv().visibility(str(_view.get("id") or ""))
        # ⭐ T2-刀26 §二（丁 · PM 拍）：唯「悬置中」（`external-pending`）方呈窗 ——
        #   已批 ／ 已拒 ／ 已释（`external-final` ／ `revoked`）⇒ ⛔ 再显（免「假窗口」）。
        _view["revoke_window"] = _vw if _vw.get("state") == "external-pending" else {"show": False}
    except Exception:
        _view["revoke_window"] = {"show": False}
    return _view


def _run_approval_gate(
    *,
    pre_terminal,
    pre_wp_list,
    guard_paused,
    messages,
    bmsg,
    data_resp,
    session_id,
    user_id,
    bridge_round,
    turn_id,
    tokens,
    tool_steps,
    bridge_exhausted,
    progress_fn,
    goal_info_fn,
    write_turn_end_fn,
    pending_cleanup_fn,
    record_escalation_fn,
):
    """S6-D4 审批卡：pre-check 终止守卫(write_pending/plan_pending/escalation_blocked) → 批量审批卡 + return。

    契约：返回 final_resp（命中终止守卫）或 None（fall through 下一轮）。原地改 _pending_writes/_plan_pending/bmsg/tool_steps。
    """
    import time

    from core.gateway.write_gate import (
        _get_pending_lock,
        _pending_cleanup,
        _pending_writes,
        _persist_pending_writes,
        _plan_pending,
    )

    # P3: pre-check 命中的终止守卫(write_pending/plan_pending/escalation_blocked) — 原语义返回
    if not guard_paused and pre_terminal is not None:
        _term_kind, _gdeny, _bfn, _bargs, _btc = pre_terminal
        if _term_kind == "write_pending":
            # R3(2026-08-30 架构根治): 批量审批卡 — 同批多个写请求合并一张卡(approve_all/selected/reject)。
            # 单请求仍走单卡(向后兼容)。_pending_writes 存批量组结构。
            _wp_batch = pre_wp_list if pre_wp_list else ([_gdeny.get("pending_write", {})] if _gdeny else [])
            pending_cleanup_fn()  # #106 C5：先清过期
            with _get_pending_lock():  # #106 C5：并发保护
                if len(_wp_batch) > 1:
                    # 批量: 主键=batch id(首个 tool_call_id), items=全部写请求
                    _batch_id = _wp_batch[0].get("id", "")
                    _pending_writes[session_id] = {
                        "id": _batch_id,
                        "batch": True,
                        "items": [dict(_p, approved=False) for _p in _wp_batch],
                        "ts": time.time(),
                    }
                else:
                    _single_pw = dict(_wp_batch[0]) if _wp_batch else {}
                    _single_pw.pop("_btc", None)
                    _single_pw.pop("_bargs", None)
                    _single_pw.pop("_bfn", None)
                    _pending_writes[session_id] = _single_pw
                _persist_pending_writes(user_id, session_id)
            _is_batch = bool(_pending_writes[session_id].get("batch"))
            _wp_count = len(_pending_writes[session_id].get("items", [])) if _is_batch else 1
            _wp_paths = ", ".join(
                str(_i.get("path") or _i.get("command", "")[:40])[:60]
                for _i in (_pending_writes[session_id].get("items", []) if _is_batch else [_pending_writes[session_id]])
            )
            print(f"[WRITE_GATE] {'批量' if _is_batch else '单'}写待确认 x{_wp_count}: {_wp_paths[:160]}")
            # ⭐ T2-刀26 §二（PM 拍 · 丁「可撒」）：写审批**悬置即入 `HoldQueue`** ⇒
            #   `_pending_card_view` 之 `revoke_window` 始 `{"show": True, "seconds_left": N}`
            #   （旧：产品侧 0 调用点 ⇒ 恒 `{"show": False}` ⇒「撤销窗口」形同虚设）。
            #   ⛔ 阻塞：唯**记**（窗口 ＝ 同一 `_PENDING_TTL` ⇒ 与 `expires_in_s` 同源）；⛔ 硬杀。
            try:
                import os as _os_h
                from core.gateway.write_gate import _PENDING_TTL as _TTL_h
                from core.pes.authorization import HoldQueue as _HQ_h

                _hid = str(_pending_writes[session_id].get("id") or "")
                _hw = int(_os_h.environ.get("PA_WRITE_HOLD_S", "0") or 0) or int(_TTL_h)
                if _hid and _hw > 0:
                    _HQ_h().hold(_hid, "write_file", _hw,
                                 {"session_id": session_id, "path": _wp_paths[:120]})
            except Exception:
                pass
            for _pi in _pending_writes[session_id].get("items", []) if _is_batch else [_pending_writes[session_id]]:
                _ptool = _pi.get("tool", _bfn or "write_file")
                _ppath = _pi.get("path") or str(_pi.get("command", ""))[:120]
                tool_steps.append(
                    {
                        "tool": _ptool,
                        "arg": str(_ppath)[:120],
                        "success": False,
                        "error": "等待老板确认写入",
                        "round": bridge_round,
                        "pending": True,
                        "pending_id": _pi.get("id", ""),
                    }
                )
            # R3(2026-08-30): 审批上下文注入 — 批量卡发出前汇总全部文件+理由(让 Agent 自查,
            # 减少无效审批; 同时给前端卡片渲染依据)
            _wp_summary = []
            for _pi in _pending_writes[session_id].get("items", []) if _is_batch else [_pending_writes[session_id]]:
                _pt = _pi.get("tool", "write_file")
                _pp = _pi.get("path") or str(_pi.get("command", ""))[:80]
                _pr = str(_pi.get("reason") or "").strip()
                _wp_summary.append(f"  - {_pt} {_pp}" + (f"（理由: {_pr[:80]}）" if _pr else "（未说明理由）"))
            bmsg["content"] = (
                (bmsg.get("content") or "")
                + chr(10)
                + chr(10)
                + f"[系统] 检测到 {'批量 ' + str(_wp_count) + ' 个' if _is_batch else ''}写操作，已暂停等待确认：{chr(10)}{chr(10).join(_wp_summary)}"
            )
            # 批138：`reason` 保持机器状态词 blocked（7-tuple 契约与 tests/unit/test_turn_reason_step1.py 依赖它）；
            # **人话进 reason_detail**（含目标 URL）。审批门这一层拿不到 guard 的 reason
            # （write_pending 的 pre_terminal 里 _gdeny 为 None，pending_write 也不带它），
            # 故用**同一单一来源** sandbox_util.exfil_note 现算 —— 只取文案，不改任何判据。
            _wp_note = ""
            try:
                from core.gateway.sandbox_util import exfil_note as _exfil_note

                _wp_items = _pending_writes[session_id].get("items", []) if _is_batch else [_pending_writes[session_id]]
                for _wi in _wp_items:
                    _n = _exfil_note(str(_wi.get("command") or ""))
                    if _n and _n not in _wp_note:
                        _wp_note = (_wp_note + "；" + _n) if _wp_note else _n
            except Exception:
                _wp_note = ""
            _wp_detail = (_wp_note + "。等待老板确认")[:300] if _wp_note else "写操作等待老板确认"
            write_turn_end_fn(session_id, turn_id, tokens, "blocked", _wp_detail, len(tool_steps))
            _resp_wp = {
                "success": True,
                "status": "write_pending",
                "data": data_resp,
                "tool_steps": tool_steps,
                "progress": progress_fn(),
                "tokens": tokens,
                "reason": "blocked",
                "reason_detail": _wp_detail,
                "goal_info": goal_info_fn(session_id),
            }
            if _is_batch:
                # Step 3.3 A：批量卡同样给一份「响应视图」（秒数由后端算，不写回 _pending_writes）
                _resp_wp["batch_pending"] = _pending_card_view(_pending_writes[session_id])
                _resp_wp["pending_writes"] = _pending_writes[session_id].get("items", [])
            else:
                _resp_wp["pending_write"] = _pending_card_view(_pending_writes[session_id])
            return (messages, tool_steps, bridge_exhausted, _resp_wp, tokens, None, None)
        if _term_kind == "plan_pending":
            # 状态写入(原内联逻辑): _plan_pending(确认路由依赖此状态)
            # 防御性保留 approved: 老板已确认(approved=True)后若 guard 再次触发 plan_pending,
            # 新状态覆盖时不得丢失 approved 标记(否则重新执行仍触发计划卡)
            _prev_pp = _plan_pending.get(session_id, {})
            _new_pp = _gdeny.get("plan_pending_info", {})
            if _prev_pp.get("approved"):
                _new_pp["approved"] = True
            _plan_pending[session_id] = _new_pp
            print(f"[PLAN_GATE] 计划确认: {_gdeny.get('plan_pending_info', {}).get('intents', 0)} 意图")
            tool_steps.append(
                {
                    "tool": _bfn,
                    "arg": str(_bargs.get("path") or "")[:120],
                    "success": False,
                    "error": "检测到多文件/多意图任务，等待老板确认计划",
                    "round": bridge_round,
                    "plan_pending": True,
                }
            )
            bmsg["content"] = (
                (bmsg.get("content") or "") + chr(10) + chr(10) + "[系统] 检测到本次任务涉及多文件/多修改点，已暂停执行并提交计划，等待老板确认后继续。"
            )
            write_turn_end_fn(session_id, turn_id, tokens, "blocked", "计划等待老板确认", len(tool_steps))
            return (
                messages,
                tool_steps,
                bridge_exhausted,
                {
                    "success": True,
                    "status": "plan_pending",
                    "data": data_resp,
                    "plan_pending_info": _plan_pending[session_id],
                    "tool_steps": tool_steps,
                    "progress": progress_fn(),
                    "tokens": tokens,
                    "reason": "blocked",
                    "reason_detail": "计划等待老板确认",
                    "goal_info": goal_info_fn(session_id),
                },
                tokens,
                None,
                None,
            )
        if _term_kind == "escalation_blocked":
            tool_steps.append(
                {
                    "tool": _bfn,
                    "arg": str(_bargs.get("path") or _bargs.get("command") or "")[:120],
                    "success": False,
                    "error": _gdeny.get("reason", "越权拦截"),
                    "round": bridge_round,
                    "escalated": True,
                }
            )
            # 断点2: 越权被拒后立即引导换路径(不等到 5 次失败) — 消息注入 + steer 通道双保险
            bmsg["content"] = (
                (bmsg.get("content") or "")
                + chr(10)
                + chr(10)
                + "[系统] 拦截越权操作: "
                + str(_gdeny.get("reason", ""))[:120]
                + "。该路径被拦截，请换沙箱内或项目根路径（clawsjoy_dev/ 或 core/、config/、data/ 相对路径），不要使用绝对路径或系统路径。"
            )
            try:
                from core.gateway.shared_state import add_steer

                add_steer(session_id, "越权路径被拦截，请立即改用沙箱内或项目根相对路径（core/、config/、data/ 等），不要重复尝试被拒路径")
            except Exception:
                pass
            # #105 越权审计落盘(与内联行为一致)
            try:
                record_escalation_fn(
                    user_id,
                    session_id,
                    _bfn,
                    str(_bargs.get("path") or _bargs.get("command") or ""),
                    _gdeny.get("reason", "越权拦截"),
                )
            except Exception:
                pass
            write_turn_end_fn(session_id, turn_id, tokens, "blocked", "越权拦截", len(tool_steps))
            return (
                messages,
                tool_steps,
                bridge_exhausted,
                {
                    "success": True,
                    "status": "escalation_blocked",
                    "data": data_resp,
                    "blocked": _gdeny.get("blocked", {}),
                    "tool_steps": tool_steps,
                    "progress": progress_fn(),
                    "tokens": tokens,
                    "reason": "blocked",
                    "reason_detail": "越权拦截",
                    "goal_info": goal_info_fn(session_id),
                },
                tokens,
                None,
                None,
            )
    return None
