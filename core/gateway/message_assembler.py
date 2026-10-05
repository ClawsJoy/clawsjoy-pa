"""消息组装模块 — 从 agent_gateway_enhanced.py 抽取

包含：
- _layer_store / _get_session_key / _layered_compress
- _assemble_messages / _safe_compress_messages
- _compress_messages（含 tool 配对修复）
- _validate_messages
"""

import json
import os
import logging
from pathlib import Path

_layer_store = {}
_layer_store_lock = None


def _get_layer_lock():
    global _layer_store_lock
    if _layer_store_lock is None:
        import threading as _th_ls

        _layer_store_lock = _th_ls.Lock()
    return _layer_store_lock


# {session_key: {"system": [], "conversation": [], "tool_previews": [], "summary": ""}}


def _get_session_key(user_id, session_id):
    return f"{user_id}::{session_id}"


def _summarize_messages_semantic(old_msgs, summary=None):
    """#41 阶段2（滚动层）：从被移出的原始消息提取语义摘要（替代占位文案）。

    结构复用 ContextManager._summary：task_goal / completed / failed_attempts /
    key_findings / in_progress / file_status。处理的是 message dict 列表。
    """
    if summary is None:
        summary = {
            "task_goal": "",
            "completed": [],
            "in_progress": "",
            "failed_attempts": [],
            "key_findings": [],
            "file_status": {},
        }
    for m in old_msgs:
        role = m.get("role", "")
        content = str(m.get("content", "") or "")[:200]
        if not content:
            continue
        # 用户消息：记录任务目标 / 进行中步骤
        if role == "user":
            if not summary["task_goal"]:
                summary["task_goal"] = content
            elif summary["task_goal"] not in summary.get("completed", []):
                pass
            if content not in summary["in_progress"] and len(content) > 4:
                summary["in_progress"] = content
        # assistant 文本：成功结论 → completed / 失败 → failed_attempts
        elif role == "assistant":
            _c = content
            if "失败" in _c or "error" in _c.lower() or "无法" in _c:
                if _c not in summary["failed_attempts"]:
                    summary["failed_attempts"].append(_c[:120])
                    if len(summary["failed_attempts"]) > 5:
                        summary["failed_attempts"] = summary["failed_attempts"][-5:]
            elif _c and not _c.startswith("[预览]") and _c not in summary["completed"]:
                # 只收结论性文本（含完成/已/成功/改为等）
                if any(k in _c for k in ("完成", "已", "成功", "改为", "新增", "修复")):
                    summary["completed"].append(_c[:120])
                    if len(summary["completed"]) > 10:
                        summary["completed"] = summary["completed"][-10:]
        # 探索性 tool 输出摘要(上下文爆炸修复): list_dir/read_file 结果摘要进 key_findings,
        # 不占热窗口 — Agent 迷失主因是 28+ 条探索 tool_result 堆满 keep=8 热窗口
        elif role == "tool":
            _tid = str(m.get("tool_call_id", "") or "")
            _tool_name = ""
            # tool 消息本身无 tool 名, 由调用方在 content 里带 [tool=xxx] 标记(见 _compress_messages 摘要化)
            if content.startswith("[tool="):
                _tool_name = content.split("]", 1)[0][len("[tool=") :]
            if _tool_name in ("list_dir", "read_file", "search_files", "query_index"):
                _kf = content[:150]
                if _kf and not any(_kf[:40] in str(f) for f in summary["key_findings"]):
                    summary["key_findings"].append(_kf)
                    if len(summary["key_findings"]) > 8:
                        summary["key_findings"] = summary["key_findings"][-8:]
    return summary


def _snapshot_to_sag(key, summary, step=0):
    """#41 阶段2（SAG 层）：摘要再溢出 → 写入 context_snapshots，返回引用指针。

    返回 {"pointer": str, "snapshot_path": str}；失败返回 None。
    """
    try:
        snap_dir = Path("data/v8/context_snapshots")
        snap_dir.mkdir(parents=True, exist_ok=True)
        _safe_key = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in key)[:60]
        snap_path = snap_dir / f"{_safe_key}_step_{step}.json"
        snap_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        # R1 落盘检索编目：snapshot 注册进 SAG（DB 不可用时静默降级）
        try:
            from core.lib.sag_audit_bridge import register_entity

            register_entity("snapshot", snap_path.name, str(summary.get("task_goal", ""))[:200], str(snap_path), [key])
        except Exception:
            pass
        return {"pointer": f"[历史快照: {snap_path.name}] 更早上下文已归档，如需回看请 read_file 读取该快照", "snapshot_path": str(snap_path)}
    except Exception as _snap_err:
        print(f"[SNAPSHOT] SAG 快照写入失败: {_snap_err}")
        return None


def _layered_compress(user_id, session_id, messages, keep=10):
    """#41 阶段2 三层滚动结构：
    热窗口（最近 keep 条）→ 滚动层（语义摘要）→ SAG 层（摘要溢出写快照 + 指针）。
    """
    # #16 P1(2026-08-29 修复): 整个读-改-写包进锁(并发竞态防护)
    # 注意: 锁内不做耗时 LLM 调用 — _summarize_messages_semantic 为纯规则提取(无 LLM), 可安全锁内
    with _get_layer_lock():
        key = _get_session_key(user_id, session_id)
        store = _layer_store.setdefault(key, {"system": [], "messages": [], "summary": ""})
        # 摘要结构升级：占位字符串 → 结构化 dict（兼容旧字符串）
        if isinstance(store.get("summary"), str):
            store["summary"] = {
                "task_goal": "",
                "completed": [],
                "in_progress": "",
                "failed_attempts": [],
                "key_findings": [],
                "file_status": {},
            }

        # 单队列按原始顺序存储
        for m in messages:
            role = m.get("role")
            if role == "system":
                store["system"] = store["system"][-2:] + [m] if len(store["system"]) >= 2 else store["system"] + [m]
            elif role in ("user", "assistant", "tool"):
                store["messages"].append(m)

        # 探索性 tool 输出摘要化(上下文爆炸修复): list_dir/read_file 长输出压缩为摘要
        # (带 [tool=xxx] 标记供语义摘要识别), 避免 28+ 条探索 tool_result 堆满热窗口
        _explore_tools = ("list_dir", "read_file", "search_files", "query_index")
        for _i in range(len(store["messages"])):
            _m = store["messages"][_i]
            if _m.get("role") != "tool":
                continue
            _c = str(_m.get("content", "") or "")
            if _c.startswith("[tool="):
                continue  # 已摘要
            if len(_c) <= 200:
                continue  # 短输出不摘要
            # 反查工具名(找对应 assistant tool_calls)
            _tid = _m.get("tool_call_id", "")
            _tname = ""
            for _mm in store["messages"]:
                for _tc in _mm.get("tool_calls") or []:
                    if _tc.get("id") == _tid:
                        _tname = str(_tc.get("function", {}).get("name", ""))
                        break
                if _tname:
                    break
            if _tname not in _explore_tools:
                continue
            # 摘要: list_dir → 文件数; read_file → 前 200 字符
            if _tname == "list_dir":
                _n = max(_c.count("\n") - 1, 0)
                _sum = f"目录共 {_n} 项: {_c[:200]}"
            else:
                _sum = _c[:200]
            store["messages"][_i] = dict(_m, content=f"[tool={_tname}] {_sum} [摘要: 原 {len(_c)} 字符]")

        # 压缩：保持 tool 配对的前提下，旧消息移出
        msgs = store["messages"]
        if len(msgs) > keep:
            # thinking 保护: 从后往前找最后一条 assistant(优先带 reasoning_content/tool_calls 的),
            # 切点不能越过它 — 否则 reasoning_content 被语义摘要替代 → DeepSeek 400
            _protect_idx = -1
            for _pi in range(len(msgs) - 1, -1, -1):
                _pm = msgs[_pi]
                if _pm.get("role") == "assistant" and (_pm.get("reasoning_content") or _pm.get("tool_calls")):
                    _protect_idx = _pi
                    break
            if _protect_idx < 0:
                # 无 thinking/tool assistant → 至少保留最后一条 assistant
                for _pi in range(len(msgs) - 1, -1, -1):
                    if msgs[_pi].get("role") == "assistant":
                        _protect_idx = _pi
                        break
            # 从前往后扫描，找第一个安全切点（tool 消息不能切在 assistant 前面）
            _cut = len(msgs) - keep
            if _protect_idx >= 0 and _cut > _protect_idx:
                # keep 太小 → 切点回退到保护位置(最后 assistant 必须留在热窗口)
                _cut = _protect_idx
            _safe_idx = 0
            for _i in range(_cut, len(msgs)):
                if msgs[_i].get("role") != "tool":
                    _safe_idx = _i
                    break
            old = msgs[:_safe_idx]
            # R2(2026-08-30 架构根治): 用户消息永不压缩 — 从被移出区抽回所有 user 原文,
            # 只摘要 tool/assistant 旧消息。用户指令是 Agent 行为锚点, 压缩丢失 → 迷失/重复探索。
            _old_all = list(old)  # ⑨(2026-09-13): 保原始顺序副本, 供语义摘要器用
            _old_users = [m for m in old if m.get("role") == "user"]
            old = [m for m in old if m.get("role") != "user"]
            # 滚动层：语义摘要（替代占位文案）
            # ⑨ 修复: 喂**剔除 user 之前**的列表 — task_goal/in_progress 的提取源就是 user
            # (message_assembler._summarize_messages_semantic 只从 role=="user" 取),
            # R2 把 user 剔除后再喂 → 这两个字段恒空(死字段), 语义摘要因此丢掉任务目标线索。
            store["summary"] = _summarize_messages_semantic(_old_all, store["summary"])
            msgs[:] = _old_users + msgs[_safe_idx:]
            # SAG 层：摘要过大（>2KB 文本）→ 写入快照 + 保留指针（防摘要自身膨胀）
            _sum_len = len(json.dumps(store["summary"], ensure_ascii=False))
            if _sum_len > 2000:
                _snap = _snapshot_to_sag(key, store["summary"], step=len(store["messages"]))
                if _snap:
                    store["summary"] = {
                        "task_goal": store["summary"].get("task_goal", ""),
                        "completed": store["summary"].get("completed", [])[-3:],
                        "in_progress": store["summary"].get("in_progress", ""),
                        "failed_attempts": store["summary"].get("failed_attempts", [])[-2:],
                        "key_findings": [],
                        "file_status": {},
                        "snapshot_pointer": _snap["pointer"],
                    }


def _summarize_text(summary):
    """把结构化摘要 dict 渲染为注入文本（供 _assemble_messages 使用）。"""
    if isinstance(summary, str):
        return summary  # 兼容旧字符串摘要
    if not isinstance(summary, dict):
        return ""
    parts = []
    if summary.get("task_goal"):
        parts.append(f"【任务目标】{summary['task_goal']}")
    if summary.get("in_progress"):
        parts.append(f"【进行中】{summary['in_progress']}")
    if summary.get("completed"):
        parts.append("【已完成】" + "；".join(summary["completed"][-5:]))
    if summary.get("failed_attempts"):
        parts.append("【失败尝试】" + "；".join(summary["failed_attempts"][-3:]))
    if summary.get("snapshot_pointer"):
        parts.append(summary["snapshot_pointer"])
    return "\n".join(parts) if parts else ""


def _assemble_messages(user_id, session_id):
    key = _get_session_key(user_id, session_id)
    # #16 P1(2026-08-29 审核修复): 读+构造 result 整个包进锁(防另一线程压缩时读竞态)
    with _get_layer_lock():
        store = _layer_store.get(key, {"system": [], "messages": [], "summary": ""})
        result = list(store["system"])
        if store["summary"]:
            _sum_text = _summarize_text(store["summary"])
            if _sum_text:
                result.append({"role": "system", "content": _sum_text})
        # 任务目标常驻(上下文爆炸修复): 即使热窗口压缩, 首条 user 消息(任务定义)始终可见 —
        # 压缩 keep=8 丢目标 → Agent 迷失 → 更多探索 → 爆炸循环的根因
        _task_goal_sys = None
        for _m in store["messages"]:
            if _m.get("role") == "user":
                _task_goal_sys = {
                    "role": "system",
                    "content": f"【任务目标】{str(_m.get('content', ''))[:300]}",
                }
                break
        if _task_goal_sys is not None:
            # 已在摘要或热窗口含原文 → 不重复; 否则前置
            _has_goal = any(str(m.get("content", "")).startswith("【任务目标】") for m in result)
            _has_raw = any(m.get("role") == "user" and m is not _task_goal_sys for m in result)
            if not _has_goal:
                # 任务目标优先注入(system 前缀, 不重复热窗口里的 user 原文)
                result = [_task_goal_sys] + [m for m in result if m is not _task_goal_sys]
        result.extend(store["messages"])
    # 唯一出口: 配对修复 + tool_calls 结构规范化(锁外做, 无 store 访问)
    return _finalize_messages(result)


def _safe_compress_messages(messages, user_id, session_id, keep=30):
    """安全压缩：保留 system 头 + 所有 user 消息 + 最近 keep 条完整消息（含 tool_calls/reasoning_content）。

    修复: 旧实现过滤带 tool_calls 的 assistant(仅留纯文本) → thinking 模式最近的
    assistant 带 tool_calls + reasoning_content 被滤掉, 配对破坏 → DeepSeek 400。
    新实现 tail 取原样消息, 由 _validate_messages 做 tool_calls/tool 配对清理,
    保证 reasoning_content 保留且不产生孤立 tool。
    R2(2026-08-30 架构根治): 用户消息永不压缩 — 所有 user 消息原文保留(任务目标/追加指令
    是 Agent 行为锚点, 压缩丢失 → 迷失/重复探索); 只压缩旧工具输出与旧 assistant。
    """
    system_msgs = [m for m in messages if m.get("role") == "system"][:2]
    user_msgs = [m for m in messages if m.get("role") == "user"]
    tail = messages[-keep:] if keep > 0 else []
    # R2: 合并所有 user(去重: tail 里已有的 user 不重复)
    _tail_user_ids = {id(m) for m in tail if m.get("role") == "user"}
    _extra_users = [m for m in user_msgs if id(m) not in _tail_user_ids]
    summary = f"【上下文摘要】中间 {len(messages) - len(system_msgs) - len(user_msgs) - len(tail)} 条消息已压缩"
    # 唯一出口: 配对修复 + tool_calls 结构规范化(根治 thinking 400)
    return _finalize_messages(system_msgs + _extra_users + [{"role": "system", "content": summary}] + tail)


def _note_compact(session_id, dropped, kept):
    """批191 · #5 补完：压缩统计上报的**唯一出口**。

    契约：只写共享态（供 done 载荷回给前端显示），失败静默（统计不是业务路径）；
    session_id 为空 ⇒ **不写**（避免污染别的 session）；dropped 不为负（防显示「已压缩 -3 条」）。
    """
    if not session_id:
        return
    try:
        from core.gateway.shared_state import set_last_compact

        set_last_compact(str(session_id), {"dropped": max(0, int(dropped)), "kept": int(kept)})
    except Exception:
        pass


def _compress_messages(messages, user_id, session_id, keep=30):
    """压缩消息列表（**压缩的唯一出口**）：保留最近 keep 条 + 任务目标；单条巨型消息按字符截断（>50KB）。

    批191 · #5 补完：三类压缩都经过本函数 —— ①入口压缩（bridge_call）②每轮压缩（round_start）
    ③截断/极端压缩（recovery）⇒ 统计在此**一处**上报，覆盖全部调用方。
    此前只在 bridge_call 的**入口压缩**上报，而入口压缩常被 derive 重建绕过（round_start.py 注释原文：
    「derive 重建后每轮压缩(治 token 爆炸——入口压缩被 derive 绕过)」）⇒ 真跑里压缩明明发生了，
    done 载荷却没有统计，「🗜 已压缩 N 条」永远不亮 = 批189 #5 的真因（不是阈值问题）。
    """
    _n_before = len(messages or [])
    _out = _compress_messages_inner(messages, user_id, session_id, keep)
    _note_compact(session_id, _n_before - len(_out or []), len(_out or []))
    return _out


def _compress_messages_inner(messages, user_id, session_id, keep=30):
    """原实现（语义未改，仅加 inner 后缀供上面的统计包装调用）。"""
    # 分层压缩
    _layered_compress(user_id, session_id, messages, keep)
    # 组装
    assembled = _assemble_messages(user_id, session_id)
    if assembled:
        return assembled
    # 兜底：旧逻辑
    # 先做安全压缩（成对保留/删除），再做原有逻辑
    messages = _safe_compress_messages(messages, user_id, session_id, keep)
    MAX_MSG_CHARS = 50 * 1024  # 单条消息最大字符数

    def _truncate_oversized(m_list):
        """削减单条巨型消息，返回是否发生截断"""
        changed = False
        for i, m in enumerate(m_list):
            content = m.get("content", "")
            if isinstance(content, str) and len(content) > MAX_MSG_CHARS:
                nm = dict(m)
                nm["content"] = content[:MAX_MSG_CHARS] + f"\n...[已截断，原长度 {len(content)} 字符]"
                m_list[i] = nm
                changed = True
        return changed

    if len(messages) <= keep:
        # 数量未超限：不直接返回，继续削减单条巨型消息，避免压缩失效
        _truncate_oversized(messages)
        # 截断后配对修复：删除没有前置 assistant tool_calls 的 tool 消息
        _valid_tc_ids = set()
        for _m in messages:
            for _tc in _m.get("tool_calls") or []:
                if isinstance(_tc, dict) and _tc.get("id"):
                    _valid_tc_ids.add(_tc["id"])
        messages[:] = [_m for _m in messages if _m.get("role") != "tool" or _m.get("tool_call_id") in _valid_tc_ids]
        # 唯一出口: 配对修复 + tool_calls 结构规范化
        messages[:] = _finalize_messages(messages)
        return messages

    head = []
    for m in messages:
        if m["role"] == "system":
            head.append(m)
        elif m["role"] == "user":
            # R2(2026-08-30): 所有 user 消息原文保留(不压缩) — 用户指令是任务锚点
            if m not in head:
                head.append(m)
        else:
            break

    # 探索性 tool 输出摘要化(上下文爆炸修复): 压缩前先把热窗口内 list_dir/read_file 的
    # 长 tool_result 压成摘要(带 [tool=xxx] 标记供 _summarize_messages_semantic 识别),
    # 避免探索性输出占满 keep 热窗口 → Agent 迷失
    def _summarize_exploratory_tool(m):
        if m.get("role") != "tool":
            return m
        _c = str(m.get("content", "") or "")
        # 已摘要过(带标记)跳过
        if _c.startswith("[tool="):
            return m
        # 从 messages 反查该 tool_call 的工具名(找对应 assistant tool_calls)
        _tid = m.get("tool_call_id", "")
        _tname = ""
        for _mm in messages:
            for _tc in _mm.get("tool_calls") or []:
                if _tc.get("id") == _tid:
                    _tname = str(_tc.get("function", {}).get("name", ""))
                    break
            if _tname:
                break
        if _tname not in ("list_dir", "read_file", "search_files", "query_index"):
            return m  # 非探索性工具全量保留
        if len(_c) <= 200:
            return m  # 短输出不需要摘要
        # 摘要: list_dir → 文件数; read_file → 前 200 字符
        if _tname == "list_dir":
            _n = max(_c.count("\n") - 1, 0)
            _sum = f"目录共 {_n} 项: {_c[:200]}"
        else:
            _sum = _c[:200]
        nm = dict(m)
        nm["content"] = f"[tool={_tname}] {_sum} [摘要: 原 {len(_c)} 字符]"
        return nm

    messages = [_summarize_exploratory_tool(m) for m in messages]
    tail = messages[-keep:]
    # 修复 tool/tool_calls 分离：如果 tail 开头是 tool 消息，往上找到对应的 assistant tool_calls 一起保留
    _tool_ids_in_tail = set()
    for _m in tail:
        if _m.get("role") == "tool" and _m.get("tool_call_id"):
            _tool_ids_in_tail.add(_m["tool_call_id"])
    if _tool_ids_in_tail:
        _extend = []
        for _m in reversed(messages[:-keep]):
            if _m.get("role") == "assistant" and _m.get("tool_calls"):
                _has = any(tc.get("id") in _tool_ids_in_tail for tc in _m["tool_calls"])
                if _has:
                    _extend.insert(0, _m)
                    break
        if _extend:
            tail = _extend + tail
    _truncate_oversized(tail)
    summary = {
        "role": "system",
        "content": f"[系统] 中间 {len(messages) - len(head) - len(tail)} 条消息已压缩(用户指令全部保留)。请基于最近对话继续。",
    }
    return head + [summary] + tail


# system_hypothesis 查询缓存（进程内存，30 秒 TTL）


def _validate_messages(messages):
    """修复 tool_calls/tool 配对：删除孤立，保证 tool 紧跟 assistant"""
    # 第一遍：收集有效 tool ids
    tool_ids = set()
    for m in messages:
        if m.get("role") == "tool" and m.get("tool_call_id"):
            tool_ids.add(m["tool_call_id"])

    # 第二遍：清理 assistant
    cleaned = []
    for m in messages:
        if m.get("role") == "assistant":
            tcs = m.get("tool_calls")
            if tcs:
                valid = [tc for tc in tcs if tc.get("id") in tool_ids]
                if valid:
                    _m = dict(m)
                    _m["tool_calls"] = valid
                    cleaned.append(_m)
                    # 把对应的 tool 消息紧跟在后面
                    for tc in valid:
                        for tm in messages:
                            if tm.get("role") == "tool" and tm.get("tool_call_id") == tc.get("id"):
                                cleaned.append(tm)
                                break
                elif m.get("content"):
                    _m = dict(m)
                    _m.pop("tool_calls", None)
                    cleaned.append(_m)
                # content=None 且无有效 tool_calls → 删除
            else:
                cleaned.append(m)
        elif m.get("role") == "tool":
            continue  # tool 消息在 assistant 循环里处理
        else:
            cleaned.append(m)

    # 第三遍：仅删除孤立 tool（不在任何 assistant 的 tool_calls 里），保留已配对的 tool 消息
    _assistant_tool_ids = set()
    for m in cleaned:
        if m.get("role") == "assistant":
            for _tc in m.get("tool_calls") or []:
                _assistant_tool_ids.add(_tc.get("id"))
    final = []
    for m in cleaned:
        if m.get("role") == "tool" and m.get("tool_call_id") not in _assistant_tool_ids:
            continue  # 孤立 tool（无对应 assistant tool_call）→ 删除
        final.append(m)

    return final


def _normalize_tool_calls(messages):
    """统一 tool_calls 结构: 补 type=function + arguments dict→json 字符串。

    根因(L 类 400): DeepSeek 要求每条 tool_calls 含 type 字段, arguments 为 json 字符串;
    经重建/回传路径(快照/压缩/回放/前端 executeToolCall)可能丢 type 或 arguments 残留 dict。
    """
    for _m in messages:
        if _m.get("role") == "assistant" and _m.get("tool_calls"):
            # 实测规则: 带 tool_calls 的 assistant 必须带 reasoning_content 字符串字段(可为空),
            # 否则 DeepSeek 400: "reasoning_content in the thinking mode must be passed back"
            # (与 thinking 开关无关 — thinking off 时缺失同样 400; None 也不行, 空字符串合法)
            if not isinstance(_m.get("reasoning_content"), str):
                _m["reasoning_content"] = ""
            for _tc in _m["tool_calls"]:
                if isinstance(_tc, dict):
                    _tc.setdefault("type", "function")
                    _fn = _tc.get("function") or {}
                    if isinstance(_fn.get("arguments"), dict):
                        _fn["arguments"] = json.dumps(_fn["arguments"], ensure_ascii=False)
    return messages


def _finalize_messages(messages):
    """DeepSeek 请求唯一出口: 配对修复(_validate_messages) + tool_calls 结构规范化(_normalize_tool_calls)。

    根治 V9 thinking 400:
    - 孤立 tool / 未配对 tool_calls / tool 前置 → _validate_messages 修复
    - 缺 type / arguments 是 dict → _normalize_tool_calls 修复
    所有"修改 messages 后发往 DeepSeek"的路径必须经此出口。
    """
    return _normalize_tool_calls(_validate_messages(messages))


_OLLAMA_CW_CACHE = {}   # ⭐ PM 2026-10-04（承 955 §五）：进程内缓存（同 model 一次 · ⛔ 每请求打 HTTP）
_CTX_SRC = {}            # ⭐ 源之记（yaml ／ ollama ／ default）⇒ 供预算归一**只**对有真窗者生效


def _get_model_context_window(model):
    """读取模型实际 context_window。

    优先从 config/v8/available_models.yaml 的模型条目中读取 context_window 配置；
    未配置时回退默认值：deepseek-v4-flash 默认 65536。
    """
    try:
        import yaml

        with open("config/v8/available_models.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for m in (data or {}).get("models", []) or []:
            if m.get("value") == model and m.get("context_window"):
                return int(m["context_window"])
    except Exception:
        pass
    # ⭐ PM 2026-10-04（承 技总 955 §五）：yaml 未命中 ⇒ 试 Ollama 真源（/api/show · 取 `*.context_length`）
    if model in _OLLAMA_CW_CACHE:
        return _OLLAMA_CW_CACHE[model]
    try:
        import urllib.request as _ur

        _base = (os.environ.get("OLLAMA_BASE_URL") or os.environ.get("CLAWSJOY_OLLAMA_BASE")
                 or "http://127.0.0.1:11434")
        _req = _ur.Request(_base.rstrip("/") + "/api/show",
                           data=json.dumps({"model": model}).encode("utf-8"),
                           headers={"Content-Type": "application/json"})
        with _ur.urlopen(_req, timeout=2) as _r:
            _j = json.loads(_r.read().decode("utf-8", "replace"))
        for _k, _v in (_j.get("model_info") or {}).items():
            if str(_k).endswith(".context_length") and _v:
                _OLLAMA_CW_CACHE[model] = int(_v)
                _CTX_SRC[model] = "ollama"
                return int(_v)
    except Exception as _e:
        print("[CTX_WINDOW] Ollama 真源不可达（model=%s）：%s: %s" % (model, type(_e).__name__, _e))
    _OLLAMA_CW_CACHE[model] = 65536
    _CTX_SRC[model] = "default"
    print("[CTX_WINDOW] 未得真源 ⇒ 回退 65536（model=%s · ⛔ 静默降级）" % model)
    return 65536


def _calc_token_budget(model="deepseek-v4-flash", tools=None):
    """计算当前模型/工具集的 Token 预算（统一所有截断决策的预算基准）。

    公式：budget = context_window - max_tokens(输出预留4000) - tg_estimate(tools)
    - context_window：模型实际上下文窗口（_get_model_context_window 读取，默认 65536）
    - max_tokens：输出预留固定 4000 tokens
    - tg_estimate(tools)：工具定义本身占用的上下文 token
    所有截断决策（TOKEN_GUARD / MSG_CAP / 主动压缩）均应以本预算为统一基准。
    """
    _cw = _get_model_context_window(model)
    _out_reserve = 4000
    _tools_est = _tg_estimate([], tools=tools) if tools else 0
    _budget = _cw - _out_reserve - _tools_est
    # ⭐ PM 2026-10-04（承 技总 955 §五）：预算 ⛔ 超「本次实到之 num_ctx」（否则静默截断 ⇒ 原病只挪位）
    #   单源：与 `llm_client` 同取 env `CLAWSJOY_NUM_CTX`；⭐ 唯对「真窗取自 Ollama」者生效（⛔ 误伤远端模型）
    if _CTX_SRC.get(model) == "ollama":
        try:
            _num_ctx = int(os.environ.get("CLAWSJOY_NUM_CTX", "8192"))
            _budget = min(_budget, _num_ctx - _out_reserve - _tools_est)
        except Exception as _e:
            print("[TOKEN_BUDGET] num_ctx 归一失败（⛔ 静默）：%s: %s" % (type(_e).__name__, _e))
    return max(_budget, 0)


# 批88：按「段落重要性」裁剪 —— 约束类段落不可裁（体检项 51）
# 事故（批87 查证）：8000 字符上限按「头 70% + 尾 30%」裁剪 agent_system.md，
#   恰好完整丢弃 ## 执行纪律(G1-G3) / ## 报告规范 / ## 执行流程（全是约束与规范类），
#   而 ## 花名册身份 这类信息段被完整保留 —— **位置先后与重要性无关**。
#   截断是静默的（不报错不打日志）⇒ 「行为约束随长度增长被悄悄削弱」。
_UNCUTTABLE_MARKS = (
    "## 执行纪律",
    "## 防幻觉硬约束",
    "## 禁止行为",
    "## 代码修改强制验证",
    "## 完成标准",
    "## 报告规范",
    "## 执行流程",
    "## 失败出口",
    "## 写操作确认",
)


def _split_uncuttable(text):
    """把 text 按 '## ' 小节切开，返回 (必须保留的块列表, 其余文本)。

    只按二级标题切；命中 _UNCUTTABLE_MARKS 的整段（标题行到下一 ## 之前）进必须保留列表。
    """
    if not text:
        return [], ""
    keep, rest = [], []
    cur_is_keep = False
    cur = []
    for line in text.split("\n"):
        if line.startswith("## "):
            if cur:
                (keep if cur_is_keep else rest).append("\n".join(cur))
            cur = [line]
            cur_is_keep = any(line.startswith(m) for m in _UNCUTTABLE_MARKS)
        else:
            cur.append(line)
    if cur:
        (keep if cur_is_keep else rest).append("\n".join(cur))
    return keep, "\n".join(rest)


def _hard_truncate_messages(messages, max_tokens=_calc_token_budget()):
    """硬截断消息列表，确保不超过安全 token 限制

    - system 消息瘦身：逐条 content 超过 8000 字符时截断为头尾摘要；
      条数超过 8 条时只保留前 4 条 + 最近 2 条，其余裁剪为摘要。
    - 非 system 消息：从最近往早保留，直到 token 上限。
    """
    # [#192] 超大 tool 结果做摘要保留：>2000 字符时保留前 300 + 后 500，中间标记截断
    for _m in messages:
        if _m.get("role") == "tool":
            _c = str(_m.get("content", "") or "")
            if len(_c) > 2000:
                _m["content"] = (
                    f"[TOOL_TRIM] tool 结果原始 {len(_c)} 字符，已摘要保留（前 300 + 后 500）。\n"
                    f"--- 开头 ---\n{_c[:300]}\n--- 截断 ---\n{_c[-500:]}"
                )

    try:
        import tiktoken as _tk

        _enc = _tk.encoding_for_model("gpt-4")
    except Exception:
        messages[:] = _finalize_messages(messages)
        return messages

    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system_msgs = [m for m in messages if m.get("role") != "system"]

    def count_tokens(msgs):
        total = 0
        for m in msgs:
            content = str(m.get("content", "")) + str(m.get("tool_calls", ""))
            total += len(_enc.encode(content))
        return total

    # —— system 消息瘦身 ——
    # 1) 逐条截断：单条 system content 超过 8000 字符时截断为头尾摘要
    _sys_limit = 8000
    for _m in system_msgs:
        _c = str(_m.get("content", "") or "")
        if len(_c) > _sys_limit:
            _keep, _rest = _split_uncuttable(_c)
            _keep_text = "\n".join(_keep)
            _budget = max(0, _sys_limit - len(_keep_text))
            _head = _rest[: int(_budget * 0.7)]
            _tail = _rest[-int(_budget * 0.3) :] if _budget else ""
            _m["content"] = (
                f"[SYS_TRIM] system 消息原始 {len(_c)} 字符，已逐条截断（不可裁段落 {len(_keep)} 段 / {len(_keep_text)} 字符，余下按头70/尾30）。\n"
                f"{_keep_text}\n--- 开头 ---\n{_head}\n--- 结尾 ---\n{_tail}"
            )
            print(f"[SYS_TRIM] 逐条截断 {len(_c)}->{len(_m['content'])} 字符；保留不可裁段落 {len(_keep)} 段")
    # 2) 条数裁剪：system 消息过多时只保留前 4 条 + 最近 2 条，其余合并为摘要
    if len(system_msgs) > 20:
        _kept_sys = system_msgs[:4] + system_msgs[-2:]
        _dropped = len(system_msgs) - len(_kept_sys)
        _kept_sys.append(
            {
                "role": "system",
                "content": f"[SYS_TRIM] 另有 {_dropped} 条 system 消息已被裁剪，如需详细信息请查看会话记录。",
            }
        )
        system_msgs = _kept_sys

    current_tokens = count_tokens(system_msgs) + count_tokens(non_system_msgs)
    if current_tokens <= max_tokens:
        return system_msgs + non_system_msgs

    # 收集 tool 消息的 tool_call_id
    tool_ids = {m["tool_call_id"] for m in non_system_msgs if m.get("role") == "tool" and m.get("tool_call_id")}

    truncated_non_system = []
    current_tokens = count_tokens(system_msgs)
    reserved_assistant_ids = set()

    for m in reversed(non_system_msgs):
        m_tokens = count_tokens([m])
        role = m.get("role")

        # tool 消息：保留，同时标记需要保留对应的 assistant
        if role == "tool":
            if current_tokens + m_tokens > max_tokens:
                break
            truncated_non_system.insert(0, m)
            current_tokens += m_tokens
            tc_id = m.get("tool_call_id")
            if tc_id:
                reserved_assistant_ids.add(tc_id)

        # assistant 消息：如果它的 tool_calls 中有被保留的 tool 结果，则保留
        elif role == "assistant" and m.get("tool_calls"):
            tc_ids = {tc.get("id") for tc in m["tool_calls"] if tc.get("id")}
            if tc_ids & reserved_assistant_ids:
                if current_tokens + m_tokens > max_tokens:
                    break
                truncated_non_system.insert(0, m)
                current_tokens += m_tokens

        # user 消息：保留最近几条
        elif role == "user":
            if current_tokens + m_tokens > max_tokens:
                break
            truncated_non_system.insert(0, m)
            current_tokens += m_tokens

    # 唯一出口: 配对修复 + tool_calls 结构规范化(根治 thinking 400)
    return _finalize_messages(system_msgs + truncated_non_system)


def _truncate_oversized_messages(messages, max_bytes=50 * 1024):
    # [MSG_CAP] 单条消息硬上限：请求体构建前，将任意单条 >50KB 的消息（content 或 tool_calls）截断并替换为摘要
    _changed = 0
    for _m in messages:
        # --- content 截断 ---
        _c = _m.get("content", "")
        if _c:
            _c_str = _c if isinstance(_c, str) else json.dumps(_c, ensure_ascii=False)
            _c_bytes = len(_c_str.encode("utf-8", errors="ignore"))
            if _c_bytes > max_bytes:
                _head = _c_str[:12000]
                _tail = _c_str[-3000:]
                _m["content"] = (
                    f"[MSG_CAP] 该条消息 content 原始 {_c_bytes // 1024}KB 超过 50KB 硬上限，已截断为摘要。\n"
                    f"--- 开头 ---\n{_head}\n--- 结尾 ---\n{_tail}"
                )
                _changed += 1
        # --- tool_calls 截断 ---
        _tcs = _m.get("tool_calls", [])
        if _tcs:
            _tcs_str = json.dumps(_tcs, ensure_ascii=False)
            _tcs_bytes = len(_tcs_str.encode("utf-8", errors="ignore"))
            if _tcs_bytes > max_bytes:
                _names = []
                for _tc in _tcs:
                    _fn = _tc.get("function", {})
                    _names.append(_fn.get("name", "?") if isinstance(_fn, dict) else "?")
                _m["tool_calls"] = [
                    {
                        "id": "msg_cap_truncated",
                        "type": "function",
                        "function": {
                            "name": ", ".join(_names[:10]) or "unknown",
                            "arguments": json.dumps(
                                {
                                    "_truncated": True,
                                    "_original_kb": _tcs_bytes // 1024,
                                    "_note": "原始 tool_calls 超过 50KB 硬上限，已替换为摘要",
                                },
                                ensure_ascii=False,
                            ),
                        },
                    }
                ]
                _changed += 1
    if _changed:
        print(f"[MSG_CAP] 单条消息硬上限触发：{_changed} 条消息被截断为摘要")
    # 唯一出口: 配对修复 + tool_calls 结构规范化
    messages[:] = _finalize_messages(messages)
    return messages


def _tg_estimate(_msgs, tools=None):
    # [TOKEN_GUARD] 估算消息列表 token 数（复用 core/lib/llm_client.py 逻辑）
    _total = 0
    try:
        import tiktoken as _tg_tk

        _tg_enc = _tg_tk.encoding_for_model("gpt-4")
        for _m in _msgs:
            _total += len(_tg_enc.encode(str(_m.get("content", "") or "")))
            for _tc in _m.get("tool_calls", []):
                _total += len(_tg_enc.encode(str(_tc)))
        # [TOKEN_GUARD] 统计 tools 定义的 tokens（若传入了 tools 参数）
        if tools:
            _total += len(_tg_enc.encode(str(tools)))
    except Exception:
        for _m in _msgs:
            _total += len(str(_m.get("content", "") or "")) * 0.5
            for _tc in _m.get("tool_calls", []):
                _total += len(str(_tc)) * 0.5
        if tools:
            _total += len(str(tools)) * 0.5
    return int(_total)


from core.gateway.message_assembler import _calc_token_budget, _get_model_context_window

logger = logging.getLogger(__name__)


# 测试效率优化: tiktoken BPE 词表首次加载 ~9.7s, 模块级缓存避免每次 _estimate_tokens 重建
_TIKTOKEN_ENC = None


def _get_tiktoken_enc():
    global _TIKTOKEN_ENC
    if _TIKTOKEN_ENC is None:
        import tiktoken

        _TIKTOKEN_ENC = tiktoken.encoding_for_model("gpt-4")
    return _TIKTOKEN_ENC


def _estimate_tokens(messages):
    """估算消息 token 数（从 agent_gateway_enhanced.py 迁移）"""
    total = 0
    try:
        enc = _get_tiktoken_enc()
        for m in messages:
            content = m.get("content", "") or ""
            total += len(enc.encode(content))
            for tc in m.get("tool_calls", []):
                total += len(enc.encode(str(tc)))
    except Exception:
        for m in messages:
            content = m.get("content", "") or ""
            total += len(content) * 0.5
            for tc in m.get("tool_calls", []):
                total += len(str(tc)) * 0.5
    return int(total)


def _inject_sys_content(messages, content, max_sys_chars=8000):
    """向 messages[0]（system）按需注入内容：去重 + 防无限 += 膨胀。

    - 按需：content 为空或 messages 为空时直接返回，不注入。
    - 去重：若 content 已存在于 messages[0]["content"]，跳过，避免无限追加。
    - 防膨胀：注入后若超过 max_sys_chars，截断保留最近内容（含注入标记头）。
    """
    if not content or not messages:
        return
    head = messages[0]
    if head.get("role") != "system":
        return
    cur = str(head.get("content", "") or "")
    if content in cur:
        return
    new_content = cur + content
    if len(new_content) > max_sys_chars:
        # 批88：与逐条截断统一 —— 先保「不可裁段落」，余下再按「保留最近」裁（体检项 51）
        _keep_b, _rest_b = _split_uncuttable(new_content)
        _keep_b_text = "\n".join(_keep_b)
        _budget_b = max(0, max_sys_chars - len(_keep_b_text))
        _kept = _rest_b[-_budget_b:] if _budget_b else ""
        new_content = (
            f"[SYS_MSG_CAP] system 注入已达上限，已截断（不可裁段落 {len(_keep_b)} 段 / {len(_keep_b_text)} 字符，余下保留最近）。原始 {len(cur) + len(content)} 字符。\n"
            + _keep_b_text
            + "\n"
            + _kept
        )
        print(f"[SYS_MSG_CAP] 注入截断：保留不可裁段落 {len(_keep_b)} 段，余下保留最近 {len(_kept)} 字符")
    head["content"] = new_content
