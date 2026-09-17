# -*- coding: utf-8 -*-
"""S5(2026-09-05): 完成判定单点 — R13 过渡语 / R15 系统回声 / 证据 的统一裁决。

各调用方(桥接 completed 收尾、goal 完成、cu 学习循环)只调用 complete_if_valid,
不再各自拼判定; goal_state.complete_goal 仅作最终执行器。
"""
_TRANSITIONAL_KW = ("准备", "将要做", "接下来", "确认可用", "做准备", "先读", "先确认", "下一步", "再跑")
_SYS_MARKERS = ("[系统]", "当前阶段：")


def detect_transitional(report):
    """R13: 短报告且含过渡词 → 视为未真正交付。"""
    r = str(report or "")
    if len(r) < 120:
        low = r.lower()
        if any(k in low for k in _TRANSITIONAL_KW):
            return True
    return False


def detect_sys_echo(report):
    """R15: 报告复读系统阶段提示且无实质内容 → 视为无产出。"""
    import re as _re

    r = str(report or "")
    if not any(m in r for m in _SYS_MARKERS):
        return False
    stripped = _re.sub(r"\[系统\][^\n]*", "", r)
    stripped = _re.sub(r"当前阶段[：:][^\n]*", "", stripped)
    stripped = _re.sub(r"\s+", " ", stripped).strip()
    return len(stripped) < 60


def verdict(report):
    """统一裁决: 过渡语/系统回声 → not deliverable。"""
    return {
        "transitional": detect_transitional(report),
        "sys_echo": detect_sys_echo(report),
        "deliverable": not (detect_transitional(report) or detect_sys_echo(report)),
    }


def complete_if_valid(user_id, session_id, report=None, evidence=None):
    """完成判定唯一入口: 判定通过 → goal_state.complete_goal(仅作执行器); 否则返回 False。

    evidence 可选: 调用方已用硬证据(如 cu completion 条件)验过再传; 判定仍要求报告可交付。
    """
    v = verdict(report)
    if not v["deliverable"]:
        return False
    try:
        from core.gateway.goal_state import complete_goal

        complete_goal(user_id or "", session_id)
        return True
    except Exception:
        return False


def _artifact_incomplete_pages(user_id, session_id, messages):
    """假完成守卫(2026-09-08): 任务要求编号页产物(PPT大纲 P1..Pn)时,
    校验产物文件是否真的含各 P 页标题 — 缺页则禁止 goal complete。
    返回 (incomplete: bool, detail: str)。"""
    import io
    import re as _re_ai

    task = ""
    for _m_ai in reversed(messages or []):
        if _m_ai.get("role") == "user":
            _t_ai = str(_m_ai.get("content") or "")
            if _t_ai and not _t_ai.startswith("[系统]"):
                task = _t_ai
                break
    pages = sorted({int(x) for x in _re_ai.findall(r"(?<![A-Z])P(\d{1,2})(?!\d)", task)})
    if len(pages) < 3:
        return False, ""  # 非编号页任务, 不拦截
    try:
        from core.gateway.sandbox_ops import _get_sandbox_base as _gsb_ai  # noqa
    except Exception:
        _gsb_ai = None
    try:
        from core.gateway.tool_router import _get_sandbox_base as _gsb_ai2
    except Exception:
        _gsb_ai2 = None
    base = None
    for _fn in (_gsb_ai2, _gsb_ai):
        if _fn:
            try:
                base = _fn(user_id, session_id)
                if base is not None:
                    break
            except Exception:
                pass
    if base is None:
        return False, ""
    import pathlib as _pl_ai

    base = _pl_ai.Path(str(base))
    # 多基座探测: 绝对 / cwd 相对 / 仓库根(网关 cwd) — 防相对基座在测试 cwd 双重前缀
    bases = [base]
    if not base.is_absolute():
        bases.append(_pl_ai.Path.cwd() / base)
        try:
            bases.append(_pl_ai.Path(__file__).resolve().parents[2] / base)
        except Exception:
            pass
    cands = []
    for _b in bases:
        try:
            cands += list(_b.glob("data/reports/*.md")) + list(_b.glob("data/reports/**/*.md"))
        except Exception:
            pass
    cands = [c for c in cands if c.is_file()]
    if not cands:
        return True, "任务要求编号页产物(data/reports/*.md)但无该文件"
    target = max(cands, key=lambda c: c.stat().st_mtime)
    content = io.open(target, encoding="utf-8").read()
    missing = []
    for pg in pages:
        if not _re_ai.search(r"^#{1,4}[ 	]*P" + str(pg) + r"", content, _re_ai.M):
            missing.append("P" + str(pg))
    if missing:
        return True, "产物 " + target.name + " 缺页: " + ",".join(missing) + " — 禁止标记完成, 请先补齐原子写入"
    return False, ""


def run_completion_guard(*, messages, data_resp, session_id, cancelled=False):
    """防假完成拦截（S5，从 _v9_bridge_loop 归位，2026-09-12）。

    契约：原地改 data_resp（content/finish_reason）；返回 messages（rollback 路径会重绑 messages，
    调用方必须 messages = run_completion_guard(...)）。cancelled 或无 data_resp 时整段跳过（no-op）。
    """
    import json
    from pathlib import Path

    from core.gateway.context_validator import _check_recent_writes, _classify_task_type, _planning_output_valid
    from core.gateway.shared_state import _fake_done_count, _guard_log

    # 防虚假完成拦截(#1 协作取消: data_resp 可能为 None 且无需防假完成 → 跳过整段)
    if cancelled or not data_resp:
        _resp_content = ""
    else:
        _resp_content = data_resp["choices"][0]["message"].get("content", "")
    # 2026-09-06 修复2+修复4(侦察后假完成): 假完成拦截的写入判定改为「任务局部扫描」,
    # 不再用 session 级累积 tracker(session 历史写残留会让本次假完成放行)。
    # 写入类工具: write_draft/update_draft/write_file/write_large/write_note/mark_published/edit_file;
    # 侦察类(read/search/list/read_file/list_dir/obsidian read/search)不算写 —
    # 写意图任务调了侦察但没落盘 = 假完成, 必须拦截。
    _task_type = _classify_task_type(messages)
    _resp_looks_done = (
        "✅ 任务完成" in _resp_content
        or "任务完成" in _resp_content
        or "已完成" in _resp_content
        or "完成如下" in _resp_content
        or "以下是修改后" in _resp_content
        or "修改前后对比" in _resp_content
    )
    _WRITE_TOOLS_FC = (
        "write_file",
        "write_large",
        "edit_file",
        "execute_command",
        "write_draft",
        "update_draft",
        "write_note",
        "mark_published",
        "update_sop",
        "append_pitfall",
    )
    _READ_TOOLS_FC = ("read_file", "list_dir", "search_files", "obsidian_knowledge")
    # 任务局部扫描: 从最近一条 user 消息之后的 assistant tool_calls 统计(不含历史任务残留)
    _fc_task_local_write = 0
    _fc_task_local_write_ok = 0
    _fc_task_local_read = 0
    _fc_scan = False
    for _m_fc in messages:
        if _m_fc.get("role") == "user":
            _fc_scan = True  # 最近 user 之后的才算本任务
            _fc_task_local_write = 0
            _fc_task_local_read = 0
            continue
        if _fc_scan and _m_fc.get("role") == "assistant":
            for _tc_fc in _m_fc.get("tool_calls") or []:
                _nm_fc = (_tc_fc.get("function") or {}).get("name", "")
                if _nm_fc in _WRITE_TOOLS_FC:
                    _fc_task_local_write += 1
                elif _nm_fc in _READ_TOOLS_FC:
                    _fc_task_local_read += 1
    # 写意图判定(用户消息含写关键词 或 任务类型写类)
    _user_wants_write_fc = any(
        _m.get("role") == "user"
        and any(
            _kw in str(_m.get("content") or "")
            for _kw in (
                "write_draft",
                "update_draft",
                "write_note",
                "草稿箱",
                "落盘",
                "调整草稿",
                "修改草稿",
                "草稿",
                "调整",
                "write_file",
            )
        )
        for _m in messages[-6:]
    )
    _task_requires_write = _task_type in ("code_modify", "delivery") or _user_wants_write_fc
    # F0.2a(2026-09-09): 契约阶段覆盖关键词裁决 — researching 阶段不要求最终写入,
    # 不触发「未写入=假完成」(研究阶段写证据台账即可, 不应被逼 heredoc 写最终文件)。
    try:
        from core.gateway.task_contract import should_require_final_write as _srw_fc

        _srw_v = _srw_fc(session_id)
        if _srw_v is False:
            _task_requires_write = False
    except Exception:
        pass
    _resp_is_errorish = (
        _resp_content.strip().startswith("⚠️")
        or _resp_content.strip().startswith("[系统]")
        or _resp_content.strip().startswith("$")
        or _resp_content.strip().startswith("预算")
        or _resp_content.strip().startswith("当前预算")
    )
    # 完成声明但本任务无写入(无论有无侦察) → 拦截; 或 写类任务停止时无写入 → 拦截
    _claimed_done_no_write = _resp_looks_done and _fc_task_local_write == 0
    _write_task_stopped_no_write = (
        _task_requires_write and _fc_task_local_write == 0 and not _resp_is_errorish and len(_resp_content.strip()) > 0
    )
    _needs_fake_check = _claimed_done_no_write or _write_task_stopped_no_write
    if _needs_fake_check:
        # 兜底: 若 execute_command 是写命令(内容含落盘操作), 从 tool 结果二次确认
        _has_write = _fc_task_local_write > 0 or _check_recent_writes(messages, session_id=session_id)
        if _task_requires_write and not _has_write:
            # 计数器：同一任务连续 3 次虚假完成则强制终止（#161）
            _task_key = session_id
            _fake_count = _fake_done_count.get(_task_key, 0) + 1
            _fake_done_count[_task_key] = _fake_count
            if _fake_count >= 3:
                _guard_log("FAKE_DONE", f"[FAKE_DONE] 连续{_fake_count}次虚假完成，回滚到上一个成功步骤", "fake_done.log")
                _fake_done_count[_task_key] = 0  # 重置计数器
                # 回滚：从 SAG steps_summary 读取该 session 最近的归档记录，注入上下文后重置对话（#166 修复）
                _last_ok_step = 0
                _rollback_msg = ""
                _rollback_ctx = ""
                try:
                    from core.lib.code_entity_extractor import extractor

                    _summaries = []
                    try:
                        # #190 任务指纹：回滚查询按 task_id 精确匹配当前任务
                        _task_fp = ""
                        _summaries = (
                            extractor.query_context_by_keywords([session_id] + ([_task_fp] if _task_fp else [])) or []
                        )
                    except Exception:
                        _summaries = []
                    # 优先取含本 session 的归档记录（v9_agent_chat / user_message_archive / auto_archive），取最近一条有内容的
                    for _s in reversed(_summaries):
                        if not isinstance(_s, dict):
                            continue
                        _task_name = str(_s.get("task_name") or "")
                        if session_id not in _task_name or (_task_fp and _task_fp not in _task_name):
                            continue
                        _sj = _s.get("summary") or {}
                        if isinstance(_sj, str):
                            try:
                                _sj = json.loads(_sj)
                            except Exception:
                                _sj = {}
                        _content = str((_sj or {}).get("content") or (_sj or {}).get("title") or "")
                        if _content.strip():
                            _last_ok_step = _s.get("step_number") or 0
                            _rollback_ctx = _content[:800]
                            break
                    # 兜底：读取 JSONL 用户消息文件（_archive_user_message 保证写入）
                    if not _rollback_ctx:
                        try:
                            _fpath = Path("data/v8/user_messages") / f"{session_id}.jsonl"
                            if _fpath.exists():
                                _usr_lines = [
                                    json.loads(_l)
                                    for _l in _fpath.read_text(encoding="utf-8").splitlines()
                                    if _l.strip()
                                ]
                                _last_usr = next((_l for _l in reversed(_usr_lines) if _l.get("role") == "user"), None)
                                if _last_usr:
                                    _rollback_ctx = str(_last_usr.get("content") or "")[:800]
                        except Exception:
                            pass
                    if _rollback_ctx:
                        _rollback_msg = f"前3次尝试均失败，已回滚到最近归档步骤（step={_last_ok_step}）。请换一种方式。"
                        _warn_msg = f"[系统拦截 #3/3] {_rollback_msg}"
                        # 真正回滚：保留 system + 用户消息，注入归档上下文
                        _sys_msgs = [m for m in messages if m.get("role") == "system"]
                        _user_msgs = [m for m in messages if m.get("role") == "user"]
                        _rollback_content = (
                            f"[回滚] 已恢复到最近归档步骤（step={_last_ok_step}）。以下是该步骤的上下文，请基于它从此处继续：\n{_rollback_ctx}"
                        )
                        messages = _sys_msgs + _user_msgs + [{"role": "system", "content": _rollback_content}]
                    else:
                        _warn_msg = f"[系统拦截 #3/3] 连续3次虚假完成。请换一种方式完成任务。"
                except Exception as _e:
                    _guard_log("FAKE_DONE", f"[FAKE_DONE] 回滚失败: {_e}", "fake_done.log")
                    _warn_msg = f"[系统拦截 #3/3] 连续3次虚假完成。请换一种方式完成任务。"
            else:
                _warn_msg = f"[系统拦截 #{_fake_count}/3] 检测到虚假完成：代码修改/交付任务未调用任何写入工具。请立即使用 execute_command 执行 python3 heredoc 脚本完成代码修改！"
            # 反馈闭环：向 messages 注入系统消息，让 Agent 感知被拦截原因与纠正方向（#192）
            messages.append(
                {
                    "role": "system",
                    "content": "[系统] 你的完成声明被判定为假完成（原因：任务要求落盘但本任务未检测到任何写入工具调用——write_draft/update_draft/write_file/write_note 均未执行，只做了侦察/计划不算完成）。请立即调用 update_draft(改已有草稿)/write_draft(新建) 完成实际写入后重新报告。",
                }
            )
            data_resp["choices"][0]["message"]["content"] = _warn_msg
            data_resp["choices"][0]["finish_reason"] = "tool_calls"
        elif _task_type == "discussion":
            # 结构化优先：tool result 中 consensus=True → 通过
            _has_consensus = False
            for _m in messages[-6:]:
                if _m.get("role") == "tool":
                    _res = _m.get("result")
                    if isinstance(_res, str):
                        try:
                            _res = json.loads(_res)
                        except Exception:
                            _res = None
                    if isinstance(_res, dict) and _res.get("consensus") is True:
                        _has_consensus = True
                        break
            # 兜底：JSON 片段 / 共识文本
            if not _has_consensus:
                _last_ctx = str(messages[-6:])
                _has_consensus = '"consensus": true' in _last_ctx or "✅ 已达成共识" in _last_ctx or "达成共识" in _last_ctx
            if not _has_consensus:
                _warn_msg = "[系统拦截] 讨论任务未达成共识，请继续讨论。"
                data_resp["choices"][0]["message"]["content"] = _warn_msg
                data_resp["choices"][0]["finish_reason"] = "tool_calls"
        elif _task_type == "planning":
            if not _planning_output_valid(messages, session_id):
                _warn_msg = "[系统拦截] 计划任务未输出计划，请先制定计划。"
                data_resp["choices"][0]["message"]["content"] = _warn_msg
                data_resp["choices"][0]["finish_reason"] = "tool_calls"
    return messages
