# -*- coding: utf-8 -*-
"""P3-B 归档层（从 v9_agent_chat 638-744 归位，2026-09-12）。

契约：
1. prepare_chat_entry(*, data, resolve_session_id_fn) -> dict
   返回 {short_circuit, messages, model, user_id, session_id, auto_sid, max_total_tools}。
2. short_circuit 非 None → 薄路由 jsonify 后直接 return（waiting_user 短路）。
3. messages 返回**新列表**（快照恢复时 = _snap_msgs + messages）；
   但对消息 dict 是**原地改**（pop 旧 reasoning_content，防 DeepSeek thinking 400）。
4. resolve_session_id_fn 以参数传入（_resolve_v9_session_id 仍在 main，防循环 import）。
"""
import json
import os
from pathlib import Path

from core.lib.paths import runtime_tmp_path


def prepare_chat_entry(*, data, resolve_session_id_fn):
    """归档层：请求体诊断 → 单数 message 兼容 → TaskContract waiting_user 短路 → 快照恢复 → RC 剥离。"""
    state = {
        "short_circuit": None,
        "messages": [],
        "model": "",
        "user_id": "",
        "session_id": "",
        "auto_sid": None,
        "max_total_tools": 16,
    }
    # #21 总工具数硬上限(前端进度条 total 同步)
    try:
        from core.gateway.shared_state import _load_v9_execution_policy

        state["max_total_tools"] = int(
            ((_load_v9_execution_policy() or {}).get("execution_budget", {}) or {}).get("max_total_tools", 16) or 16
        )
    except Exception:
        state["max_total_tools"] = 16
    messages = data.get("messages", [])
    # 2026-09-06 诊断: dump 前端实际发送的 messages 结构(定位 reasoning 400 触发源)
    try:
        _reqdbg = {
            "n": len(messages),
            "msgs": [
                {
                    "role": m.get("role"),
                    "has_rc": "reasoning_content" in m,
                    "rc": type(m.get("reasoning_content")).__name__ if "reasoning_content" in m else None,
                    "has_tc": bool(m.get("tool_calls")),
                    "tc_n": len(m.get("tool_calls") or []),
                    "content_head": str(m.get("content") or "")[:60],
                }
                for m in messages
            ],
        }
        with open(runtime_tmp_path("v9_req_dump.json"), "w", encoding="utf-8") as _f_reqdbg:
            _f_reqdbg.write(json.dumps(_reqdbg, ensure_ascii=False, indent=1))
    except Exception:
        pass
    # #93 兼容：单数 message 字段（curl/手动调用）自动包装为 messages 列表
    if not messages and data.get("message"):
        messages = [{"role": "user", "content": data["message"]}]
    # [ENTRY_MSG] 诊断: 环境变量 V9_ENTRY_MSG_DEBUG=1 才打印(防生产刷屏)
    try:
        if os.environ.get("V9_ENTRY_MSG_DEBUG") == "1":
            _last_m = messages[-1] if messages else {}
            print(
                f"[ENTRY_MSG] messages数={len(messages)} 最后一条={_last_m.get('role','?')}: {str(_last_m.get('content',''))[:80]}",
                flush=True,
            )
    except Exception:
        pass
    # H1 修复：user_id/session_id/model 提前定义（原在快照恢复之后，快照段用未定义变量被 except 吞 → 从未恢复）
    model = data.get("model", os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"))
    user_id = data.get("user_id", "default")
    session_id, _auto_sid = resolve_session_id_fn(user_id, data.get("session_id", "default"))
    state.update(
        {"messages": messages, "model": model, "user_id": user_id, "session_id": session_id, "auto_sid": _auto_sid}
    )

    # F0.2b(2026-09-09): TaskContract 入口 — waiting_user 运行时短路 + 自动编译绑定(仅非 stream 同步)
    try:
        from core.gateway.task_contract import compile_contract as _cc_b
        from core.gateway.task_contract import contract_for_session as _cfs_b
        from core.gateway.task_contract import dispatch as _dsp_b
        from core.gateway.task_contract import ensure_contract as _enc_b
        from core.gateway.task_contract import user_answer as _ua_b
        from core.gateway.task_contract import waiting_user_payload as _wup_b

        _wu_b = _wup_b(session_id)
        if _wu_b:
            _last_u_b = ""
            for _m_b in reversed(messages):
                if _m_b.get("role") == "user" and str(_m_b.get("content") or "").strip():
                    _last_u_b = str(_m_b.get("content") or "")
                    break
            _is_auto = _last_u_b.startswith("[系统]") or not _last_u_b.strip()
            _is_new_task = (not _is_auto) and (_cc_b("t_probe", _last_u_b) is not None) and len(_last_u_b) > 20
            if _is_auto:
                # waiting_user 短路：回给薄路由 jsonify
                state["short_circuit"] = {
                    "success": True,
                    "status": "waiting_user",
                    "reason": "waiting_user",
                    "question": _wu_b.get("question", ""),
                    "options": _wu_b.get("options", []),
                    "data": {
                        "choices": [
                            {"message": {"role": "assistant", "content": "[等待确认] " + str(_wu_b.get("question", ""))}}
                        ]
                    },
                }
                return state
            if _is_new_task:
                _enc_b(session_id, "task_" + str(int(__import__("time").time())), _last_u_b)
            else:
                _cur_b = _cfs_b(session_id)
                if _cur_b is not None:
                    _dsp_b(_cur_b.get("task_id"), _cur_b, _ua_b(_last_u_b[:200]))
                    print("[CONTRACT] waiting_user 收到答复, 已推进")
    except Exception as _e_b:
        print(f"[CONTRACT] 入口接线异常(忽略): {_e_b}")
    # 消息历史快照恢复：重启后自动恢复最近 20 条消息
    try:
        _snap_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.task_state.json")
        if _snap_file.exists():
            _snap = json.loads(_snap_file.read_text(encoding="utf-8"))
            _snap_msgs = _snap.get("messages", [])
            _snap_task = _snap.get("task_name", "")
            if _snap_msgs and len(_snap_msgs) > len(messages):
                # thinking 400 修复: 快照含旧 assistant 的 reasoning_content,
                # DeepSeek 只接受最近一次 thinking 的 reasoning_content —
                # 恢复后 messages = 旧快照 + 当前消息会形成多条 reasoning_content 冲突 → 400。
                # 剥离所有旧消息的 reasoning_content(仅保留角色/内容/工具调用)。原地改 dict。
                for _m in _snap_msgs:
                    if _m.get("role") == "assistant":
                        _m.pop("reasoning_content", None)
                messages = _snap_msgs + messages  # 返回新列表
                messages.append(
                    {"role": "system", "content": f"[系统] 已从快照恢复 {len(_snap_msgs)} 条历史消息。上次任务：{_snap_task[:60]}"}
                )
    except Exception:
        pass
    # 2026-09-06 修复: 入口 assistant reasoning_content 统一剥离(防 thinking 400，原地改 dict)
    try:
        _stripped_rc = 0
        for _m_rc in messages:
            if _m_rc.get("role") == "assistant" and _m_rc.get("reasoning_content") is not None:
                _m_rc.pop("reasoning_content", None)
                _stripped_rc += 1
        if _stripped_rc:
            print(f"[RC_STRIP] 入口剥离 {_stripped_rc} 条 assistant reasoning_content(防 thinking 400)")
    except Exception:
        pass
    state["messages"] = messages
    return state
