# -*- coding: utf-8 -*-
"""P3-A 辅助函数归位：写/计划审批处理（从 agent_gateway_enhanced.py 迁入，2026-09-12）。"""
import json
import time

from flask import jsonify

from core.gateway.audit import _record_approval
from core.gateway.tool_router import _truncate_tool_result_content
from core.gateway.write_gate import _pending_writes, _persist_pending_writes, _plan_pending


def _approval_payload(_r):
    """把「审批回执分发」的返回统一成 **可 JSON 序列化的 dict**（批146 修契约）。

    契约来源：core/gateway/v9_chat/entry.py:36 ——「返回 (payload, kind)；"json" → 路由 jsonify」。
    本模块的 helpers（_handle_write_approval / _handle_plan_approval）历史上直接 return jsonify(...)
    （Flask Response；该形态被 tests/unit/test_workspace_guard_fixes.py 直接断言），一旦被
    recover_session 放进 short_circuit，路由再 jsonify(payload) 就会
        TypeError: Object of type Response is not JSON serializable → HTTP 500。
    因此**只在这唯一出口**把 Response 还原成 dict：helpers 的既有形态不动，契约在边界上统一。
    """
    if _r is None or isinstance(_r, dict):
        return _r
    _gj = getattr(_r, "get_json", None)
    if callable(_gj):
        try:
            return _gj(silent=True)
        except Exception:
            return {"success": False, "error": "审批回执序列化失败"}
    return _r


def _handle_plan_approval(user_id, session_id, messages, model, approve):
    """#101 G2 老板确认/拒绝多文件计划后，放行桥接执行或注入调整指令。

    approve: {"action": "approve"|"reject"}
    """
    _p = _plan_pending.get(session_id)
    if not _p:
        return jsonify({"success": False, "error": "待确认的计划不存在或已过期，请重新执行任务。"})
    _action = approve.get("action", "")
    if _action == "approve":
        _plan_pending[session_id]["approved"] = True
        print(f"[PLAN_GATE] 老板确认计划: {_p.get('intents')} 意图 / {len(_p.get('files', []))} 文件")
        _record_approval(
            user_id,
            session_id,
            "plan",
            "approved",
            _p.get("plan", "")[:120],
            f"{_p.get('intents')} 意图 / {len(_p.get('files', []))} 文件",
        )
        # #101 G6 目标持久：把确认的计划写入 goal.plan
        try:
            from core.gateway.goal_state import _goals, _load_state, _save_state, get_goal

            _goal_cur = get_goal(user_id, session_id)
            if _goal_cur:
                _goal_cur["plan"] = _p.get("plan", "")[:500]
                _goal_cur["updated_at"] = time.time()
                _goals[f"{user_id}:{session_id}"] = _goal_cur
                _st_g = _load_state(user_id, session_id)
                _st_g["goal"] = _goal_cur
                _save_state(user_id, session_id, _st_g)
        except Exception as _goal_plan_err:
            print(f"[GOAL_STATE] 计划写入 goal 失败: {_goal_plan_err}")
        # 放行：重新进入桥接执行（同一 messages，plan_pending approved=True 后跳过计划门）
        return jsonify(
            {
                "success": True,
                "status": "plan_confirmed",
                "message": "计划已确认，继续执行。",
                "continue_messages": messages,
            }
        )
    elif _action == "reject":
        _plan_pending.pop(session_id, None)
        print(f"[PLAN_GATE] 老板拒绝计划: {_p.get('intents')} 意图 / {len(_p.get('files', []))} 文件")
        _record_approval(
            user_id,
            session_id,
            "plan",
            "rejected",
            _p.get("plan", "")[:120],
            f"{_p.get('intents')} 意图 / {len(_p.get('files', []))} 文件",
        )
        _reject_msg = {
            "role": "system",
            "content": (
                f"[系统] 老板拒绝了本次计划（涉及 {_p.get('intents')} 个修改点：{', '.join(_p.get('files', []))[:200]}）。"
                "请调整方案（缩小改动范围 / 更换文件 / 分步执行并说明理由）后重新提出，不要重复原计划。"
            ),
        }
        messages = messages + [_reject_msg]
        return jsonify(
            {
                "success": True,
                "status": "plan_rejected",
                "message": "已拒绝该计划，Agent 将调整方案。",
                "tool_steps": [],
                "continue_messages": messages,
            }
        )
    return jsonify({"success": False, "error": "未知的确认动作"})


def _handle_write_approval(user_id, session_id, messages, model, approve):
    """老板确认/拒绝写操作后，继续桥接执行或注入拒绝原因。

    approve: {"id": tool_call_id, "action": "approve"|"reject"|"approve_all"|"approve_selected", "ids": [...], "messages": [...]}
    R3(2026-08-30): 批量审批卡 — action=approve_all 全批; approve_selected 按 ids 列表; reject 全拒。
    """
    import threading as _th_wa

    _p = _pending_writes.get(session_id)
    _is_batch = bool(_p and _p.get("batch"))
    if _is_batch:
        # 批量: id 校验宽松(主键=batch 首个 id; 或 action 显式批量动作)
        if _p.get("id") != approve.get("id") and approve.get("action") not in ("approve_all", "approve_selected"):
            _expired_flag = _p is None
            return jsonify(
                {
                    "success": False,
                    "status": "write_expired" if _expired_flag else "write_confirmed_dup",
                    "message": "该写入审批已过期或已完成。请让 Agent 重新发起写入。",
                    "expired": True if _expired_flag else False,
                }
            )
    elif not _p or _p.get("id") != approve.get("id"):
        # 2026-08-30 审核对齐 harness: pending 不存在 = 已执行过 或 TTL(60s) 已过期。
        # 不再返回"已确认执行"假成功(用户点卡片后发现没写入, 误以为成功) —
        # 过期场景前端显示明确提示, Agent 需重新发起写入。
        _expired_flag = _p is None
        if _expired_flag:
            print(f"[WRITE_GATE] 审批目标不存在(可能已过期/已执行): {approve.get('id')}")
        return jsonify(
            {
                "success": False,
                "status": "write_expired" if _expired_flag else "write_confirmed_dup",
                "message": "该写入审批已过期或已完成（60 秒内有效）。请让 Agent 重新发起写入；如需原内容请重新触发。",
                "expired": True if _expired_flag else False,
            }
        )
    _action = approve.get("action", "")
    # 批153 · 卡片三选项：action="always" = 本次照做 **且记住该场景**（下次免问）
    if _action == "always":
        try:
            from core.pa.grants import grant as _grant_fn
            from core.pa.grants import scene_of as _scene_of

            _pw = _pending_writes[session_id] or {}
            _sc = _scene_of(_pw.get("tool", ""), {"path": _pw.get("path", ""), "command": _pw.get("command", "")})
            if _sc:
                _grant_fn(_sc, "always", note="老板在审批卡选择「一直允许」")
                print("[GRANT] 已记住授权场景: %s" % _sc)
            else:
                print("[GRANT] 场景为空，未记住（该写操作每次仍会问）")
        except Exception as _ge:
            print("[GRANT_FAIL] %s" % _ge)
        _action = "approve"
    if _action in ("approve", "approve_all", "approve_selected"):
        _pending_writes[session_id]["approved"] = True
        if _is_batch:
            # R3 批量: 选择批准的子集(approve_all=全部; approve_selected=ids 匹配)
            _sel_ids = set(approve.get("ids") or []) if _action == "approve_selected" else None
            _items = _pending_writes[session_id].get("items", [])
            _approved_items = []
            for _it in _items:
                if _sel_ids is None or _it.get("id") in _sel_ids:
                    _approved_items.append(_it)
            if not _approved_items:
                return jsonify({"success": False, "error": "未选择任何要批准的写入", "status": "batch_no_selection"})
            print(f"[WRITE_GATE] 老板批量确认 {len(_approved_items)}/{len(_items)} 个写入")
            for _it in _approved_items:
                _record_approval(
                    user_id, session_id, "write", "approved", _it.get("path", ""), f"tool={_it.get('tool')} batch"
                )
                try:
                    from core.gateway.shared_state import mark_file_approved

                    _ap2 = str(_it.get("path") or "")
                    if _ap2:
                        mark_file_approved(session_id, _ap2)
                except Exception:
                    pass
            # 逐项执行(复用 _resume_bridge_after_approval 单件逻辑)
            for _it in _approved_items:
                try:
                    _resp_b = _resume_bridge_after_approval(user_id, session_id, messages, model, _it)
                except Exception as _be:
                    print(f"[WRITE_GATE] 批量项执行失败: {_be}")
            # 未批准的项保留在 pending(可再批); 全批完则清除
            # 修正(2026-08-30): approve_all(_sel_ids=None) 时 remaining 应为空;
            # 原 `_sel_ids is None or ...` 恒 True 导致 remaining=全部, pending 不清理(残留 bug)
            if _sel_ids is None:
                _remaining = []
            else:
                _remaining = [i for i in _items if i.get("id") not in _sel_ids]
            if _remaining:
                _pending_writes[session_id]["items"] = _remaining
            else:
                _pending_writes.pop(session_id, None)
            _persist_pending_writes(user_id, session_id)
            return jsonify(
                {
                    "success": True,
                    "status": "batch_confirmed",
                    "message": f"已批准 {len(_approved_items)} 个写入并执行。",
                    "tool_steps": [],
                    "continue_messages": messages,
                }
            )
        # 单件(原逻辑)
        _pending_writes[session_id]["approved"] = True
        print(f"[WRITE_GATE] 老板确认写入: {_p.get('tool')} {_p.get('path','')[:80]}")
        _record_approval(user_id, session_id, "write", "approved", _p.get("path", ""), f"tool={_p.get('tool')}")
        # 确认即标记文件已批准(2026-08-29): 即使执行失败(覆盖保护等), 同文件后续 write 免审,
        # 防 Agent 分片/重试同一文件反复弹审批卡片(多卡片时前端按钮禁用 → 后续点无效)
        try:
            from core.gateway.shared_state import mark_file_approved

            _ap_path = str(_p.get("path") or "")
            if _ap_path:
                mark_file_approved(session_id, _ap_path)
        except Exception:
            pass
        # 重新触发桥接执行：复用同一 messages + 写放行标记
        # 由于写操作在桥接循环内拦截，此处直接以放行状态再次进入 v9_agent_chat 主流程
        # 通过 _pending_writes[session_id]["approved"]=True + 相同 tool_call_id 放行
        _resp = _resume_bridge_after_approval(user_id, session_id, messages, model, _p)
        return _resp
    elif _action == "reject":
        _pending_writes.pop(session_id, None)
        _persist_pending_writes(user_id, session_id)  # #106 清除持久化
        print(f"[WRITE_GATE] 老板拒绝写入: {_p.get('tool')} {_p.get('path','')[:80]}")
        _record_approval(user_id, session_id, "write", "rejected", _p.get("path", ""), f"tool={_p.get('tool')}")
        _reject_msg = {
            "role": "system",
            "content": f"[系统] 老板拒绝了写操作 {_p.get('tool')}（{_p.get('path','')[:120]}）。请调整方案（换文件/换路径/说明理由）后重新提出写入，不要重复原写入。",
        }
        messages = messages + [_reject_msg]
        # 拒绝后：返回 continue_messages 供前端继续桥接（Agent 调整方案后重新提出写入）
        return jsonify(
            {
                "success": True,
                "status": "write_rejected",
                "message": "已拒绝该写入，Agent 将调整方案。",
                "tool_steps": [],
                "continue_messages": messages,
            }
        )
    return jsonify({"success": False, "error": "未知的确认动作"})


def _resume_bridge_after_approval(user_id, session_id, messages, model, pending):
    """确认后放行写操作：把 pending 的写 tool_call 注入 messages 并走真实执行。

    由于写操作已在桥接循环内被拦截返回，此处直接执行该写操作并回填结果，
    然后返回给前端继续桥接（前端会带放行标记再次调用）。
    """
    import json as _json_wa

    from core.gateway.tool_router import _execute_sandbox_tool as _exec_wa

    # 构造写 tool_call: 优先从 messages 反查原始完整 tool_call 参数(含完整 content/edits),
    # 避免使用 content_preview(500字符截断) 导致确认后写入的文件被截断 (BUG-20260824-1)
    _bargs_wa = {}
    try:
        for _m_wa in messages:
            for _tc_wa in _m_wa.get("tool_calls") or []:
                if _tc_wa.get("id") == pending.get("id"):
                    _raw_args = _json_wa.loads(_tc_wa["function"]["arguments"])
                    if isinstance(_raw_args, dict):
                        _bargs_wa = _raw_args
                    break
            if _bargs_wa:
                break
    except Exception:
        _bargs_wa = {}
    if not _bargs_wa:
        # fallback: 从 pending 内容构造(兼容无 tool_calls 上下文/恢复场景)
        # 完整内容优先(full_content, 2026-08-29 修复): content_preview 是 500 字符截断,
        # 覆盖大文件时用 preview 会导致新内容被截断 → 相似度 0% 误拒绝
        if pending.get("path"):
            _bargs_wa["path"] = pending["path"]
        if pending.get("content"):
            _bargs_wa["content"] = pending["content"]
        elif pending.get("content_preview"):
            _bargs_wa["content"] = pending["content_preview"]
        if pending.get("command"):
            _bargs_wa["command"] = pending["command"]
    # P1 S6: 审批已确认放行, pre-guards 传 approved 标记(不重复触发 write_pending)
    try:
        from core.gateway.guards.runner import run_post_guards, run_pre_guards

        _gdeny_wa = run_pre_guards(
            {
                "tool": pending.get("tool", "write_file"),
                "args": _bargs_wa,
                "user_id": user_id,
                "session_id": session_id,
                "sandbox_base": str(
                    __import__("core.lib.gateway_helpers", fromlist=["_get_sandbox_base"])._get_sandbox_base(
                        user_id, session_id
                    )
                ),
                "messages": messages,
                "tool_call_id": pending.get("id", ""),
                "approved": {"id": pending.get("id", ""), "approved": True},
            }
        )
        if _gdeny_wa is not None and _gdeny_wa.get("status") not in ("write_pending", "plan_pending"):
            _btr_wa = {"success": False, "error": _gdeny_wa.get("reason", "确认后执行被拒绝"), "guard_denied": True}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": pending.get("id", ""),
                    "content": _truncate_tool_result_content(json.dumps(_btr_wa, ensure_ascii=False, default=str)),
                }
            )
            print(f"[WRITE_GATE] 确认后执行被 guard 拒绝: {_gdeny_wa.get('reason', '')[:80]}")
            # 残留修复: guard 拒绝也要清除 pending(避免 approved=True 残留 → 卡片重复「待确认」)
            try:
                if _pending_writes.get(session_id) and _pending_writes[session_id].get("id") == pending.get("id"):
                    _pending_writes.pop(session_id, None)
                    _persist_pending_writes(user_id, session_id)
            except Exception:
                pass
            return
    except Exception:
        pass
    # 死循环修复: 审批确认通过 → 记录该文件已批准指纹(同 session 后续写入免审)
    try:
        from core.gateway.shared_state import mark_file_approved

        _approved_path = str(_bargs_wa.get("path") or pending.get("path") or "")
        if _approved_path:
            mark_file_approved(session_id, _approved_path)
        # execute_command 写命令: 批准后记录命令指纹(同命令后续免审, 2026-08-30)
        if pending.get("tool") == "execute_command" and _bargs_wa.get("command"):
            mark_file_approved(session_id, "cmd:" + str(_bargs_wa.get("command"))[:120])
    except Exception:
        pass
    _btr_wa = _exec_wa(pending.get("tool", "write_file"), _bargs_wa, user_id, session_id)
    # P1 S6: post 观察(审计/计数)
    try:
        run_post_guards(
            {
                "tool": pending.get("tool", "write_file"),
                "args": _bargs_wa,
                "user_id": user_id,
                "session_id": session_id,
                "result": _btr_wa,
                "agent_id": session_id,
            }
        )
    except Exception:
        pass
    # P2a 事件溯源: 确认后的写执行补记 tool_call + tool_result(否则 derive_messages 投影
    # 出现无 tool result 的 write tool_call → DeepSeek 400 insufficient tool messages)
    _btr_wa_content = json.dumps(_btr_wa, ensure_ascii=False, default=str)
    try:
        from core.gateway.session_log import log_event

        log_event(
            session_id,
            "tool_call",
            {"name": pending.get("tool", "write_file"), "arguments": _bargs_wa, "call_id": pending.get("id", "")},
            turn_id=-1,
            step_id=0,
        )
        log_event(
            session_id,
            "tool_result",
            {
                "name": pending.get("tool", "write_file"),
                "call_id": pending.get("id", ""),
                "content": _truncate_tool_result_content(_btr_wa_content),
                "success": bool(_btr_wa.get("success")) if isinstance(_btr_wa, dict) else False,
            },
            turn_id=-1,
            step_id=1,
        )
    except Exception as _le_wa:
        print(f"[WRITE_GATE] 确认后事件补记失败: {_le_wa}")
    # 回填 tool 结果到 messages（保持上下文连续）
    messages.append(
        {
            "role": "tool",
            "tool_call_id": pending.get("id", ""),
            "content": _truncate_tool_result_content(_btr_wa_content),
        }
    )
    print(f"[WRITE_GATE] 确认后执行: {pending.get('tool')} → success={_btr_wa.get('success')}")
    # 审核机制修复(2026-08-30, 参考 harness): 确认后执行失败 → 显式注入失败原因 +
    # 换路径指引, 阻止 Agent 用同一全量覆盖方式反复重试触发新审批(用户确认 N 次循环)
    if isinstance(_btr_wa, dict) and not _btr_wa.get("success") and _btr_wa.get("error"):
        _fail_note = f"[系统] 写操作已确认但执行失败：{_btr_wa.get('error')}"
        _hint_wa = _btr_wa.get("hint")
        if _hint_wa:
            _fail_note += f" {_hint_wa}"
        _fail_note += " 请改用系统建议的方式（如 line 参数精确修改单行 / 先 read 完整内容 / 用 append 追加），不要重复全量覆盖同一文件。"
        messages.append({"role": "system", "content": _fail_note})
        print(f"[WRITE_GATE] 确认后失败已注入指引: {str(_btr_wa.get('error'))[:80]}")
    # 确认后写入完成 → 清除 pending(防止同一文件重复出现「待确认」; 下一次写是新的审批)
    try:
        if _pending_writes.get(session_id) and _pending_writes[session_id].get("id") == pending.get("id"):
            _pending_writes.pop(session_id, None)
            _persist_pending_writes(user_id, session_id)  # #106 同步清除持久化
            print("[WRITE_GATE] 确认后 pending 已清除")
    except Exception as _pe_wa:
        print(f"[WRITE_GATE] pending 清除失败(忽略): {_pe_wa}")
    return jsonify(
        {
            "success": True,
            "status": "write_confirmed",
            "tool_result": _btr_wa,
            "message": "已确认写入并执行完成。",
            "continue_messages": messages,
        }
    )


def _v9_handle_approvals(data, messages, model, user_id, session_id):
    """H1 提取: 锚点A写确认 + G2计划确认回执 + P2 浏览器操作确认分发。有回执返回 jsonify, 否则 None。"""
    # #102 锚点A：写操作确认回执（approve/reject）
    _approve = data.get("approve_write")
    if _approve and isinstance(_approve, dict) and _approve.get("id"):
        return _approval_payload(_handle_write_approval(user_id, session_id, messages, model, _approve))
    # #101 G2 计划确认回执（approve/reject）
    _plan_approve = data.get("approve_plan")
    if _plan_approve and isinstance(_plan_approve, dict) and _plan_approve.get("action") in ("approve", "reject"):
        return _approval_payload(_handle_plan_approval(user_id, session_id, messages, model, _plan_approve))
    # P2 本地浏览器操作确认回执（approve_browser: {op_id, action: approve|reject}）
    _br_approve = data.get("approve_browser")
    if _br_approve and isinstance(_br_approve, dict) and _br_approve.get("op_id"):
        from core.lib.v8 import browser_local as _bl_p2

        _br_act = _br_approve.get("action") in ("approve", "reject")
        if _br_act:
            _br_res = _bl_p2.approve_browser_op(user_id, _br_approve["op_id"], _br_approve["action"] == "approve")
            if _br_res.get("success"):
                return {
                    "success": True,
                    "status": "browser_confirmed" if _br_approve["action"] == "approve" else "browser_rejected",
                    "message": "浏览器操作已确认并执行。" if _br_approve["action"] == "approve" else "已拒绝浏览器操作。",
                    "result": _br_res,
                    "continue_messages": messages,
                }
            return {"success": False, "error": _br_res.get("error", "浏览器操作确认失败")}
    # P4 回复审批回执（approve_reply: {reply_id, approve}）
    _rp_approve = data.get("approve_reply")
    if _rp_approve and isinstance(_rp_approve, dict) and _rp_approve.get("reply_id"):
        from core.lib.v8 import browser_local as _bl_p4

        _rp_res = _bl_p4.approve_reply(
            user_id,
            _rp_approve["reply_id"],
            bool(_rp_approve.get("approve")),
            reply_text=str(_rp_approve.get("reply_text", "") or ""),
        )
        return _rp_res if isinstance(_rp_res, dict) else _approval_payload(_rp_res)
    return None
