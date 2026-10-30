"""会话控制路由（P1 拆出，Blueprint）—— 薄包装 → core.gateway.{replay,shared_state,subtask_executor,goal_state,session_log}"""

import json

from flask import Blueprint, jsonify, request

bp = Blueprint("session_routes", __name__)


def _missing(_key):
    """必填缺失 ⇒ 400 ＋ 定位（PM-011 N11：同一键 ⛔ 不许两套码；形制 `<路由>: 缺 <键>`）。

    ⭐ T2-刀8 §三（2026-10-05 · PM 裁「准办」）：**只增** `missing` ＋ `kind` 两键 ——
      由：面之「**0 件**」与「**缺参 400**」同形而 ⛔ 可辨 ⇒ 读者误把错渲染成空（承「空 ⛔ 混 缺」）。
      ⛔ 破既有 `400` 之形（`success:false` ＋ `error` 逐字保 · 承裁「只增键」）。
    """
    _rule = request.url_rule
    _rt = (_rule.rule if _rule is not None else "?").lstrip("/")
    return (
        jsonify(
            {"success": False, "error": f"{_rt}: 缺 {_key}", "missing": [_key], "kind": "missing_param", "route": _rt}
        ),
        400,
    )


@bp.route("/v9/replay/<path:session_id>", methods=["GET"])
def v9_replay_session(session_id):
    """#6: LLM 端到端回放 — 从 SessionLog 事件日志重建完整对话(LLM 调用输入等价)。

    GET /v9/replay/{session_id}?at_turn=N&verify=1
    - at_turn=N: 回放到第 N 轮 LLM 调用前的输入窗口(逐轮 step-through)
    - verify=1:  附加一致性校验(角色白名单 / tool 配对 / 与 derive_messages 交叉一致)
    """
    try:
        _at = request.args.get("at_turn")
        from core.gateway.replay import replay_session, verify_replay

        _rep = replay_session(session_id, at_turn=int(_at) if _at else None)
        if request.args.get("verify") == "1":
            _rep["verify"] = verify_replay(session_id)
        return jsonify(_rep)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)[:300]}), 500


@bp.route("/v9/cancel/<path:session_id>", methods=["POST"])
def v9_cancel_session(session_id):
    """#1 协作取消: 置位取消标志(bridge_loop 下轮检查点退出, 不硬杀)。

    前端停止按钮调用; 工具执行中的取消不中断当前工具, 标记后下轮退出。
    """
    try:
        from core.gateway.shared_state import request_cancel

        request_cancel(session_id)
        # 同步关 turn_registry：否则 active 守卫仍见 RUNNING、心跳还会续，停按钮等于没停。
        from core.gateway import turn_registry as _tr

        _closed = []
        for _t in _tr.list_turns(session_id=session_id, limit=50):
            if _t.get("status") in ("CREATED", "RUNNING", "DETACHED"):
                _tr.finish_turn(_t["turn_key"], "CANCELLED", "用户停止")
                _closed.append(_t["turn_key"])
        print(f"[CANCEL] POST /v9/cancel/{session_id} closed={_closed}")
        return jsonify({"success": True, "cancelled": True, "session_id": session_id, "closed": _closed})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)[:200]}), 500


@bp.route("/v9/preempt", methods=["POST"])
def v9_preempt():
    """#12 工具优先级抢占: 高优先级任务登记抢占请求, 打断正在执行的低优工具。

    body: {session_id, priority(数字越大越紧急, 建议4+), reason, target_tool(可选), requester(可选)}
    调度器(工具执行入口)每工具前检查: 当前工具优先级 < 请求优先级 → 返回 preempted 结果。
    """
    _pj = request.json or {}
    _pj_sid = _pj.get("session_id", "")
    if not _pj_sid:
        return _missing("session_id")
    try:
        from core.gateway.shared_state import request_preempt

        request_preempt(
            _pj_sid,
            priority=int(_pj.get("priority", 5) or 5),
            reason=str(_pj.get("reason", "紧急任务抢占")),
            target_tool=_pj.get("target_tool"),
            requester=str(_pj.get("requester", "boss")),
        )
        print(f"[PREEMPT] POST /v9/preempt session={_pj_sid} prio={_pj.get('priority', 5)}")
        return jsonify({"success": True, "preempted_queued": True, "session_id": _pj_sid})
    except Exception as _pj_err:
        return jsonify({"success": False, "error": str(_pj_err)[:200]}), 500


@bp.route("/v9/subtask/create", methods=["POST"])
def v9_subtask_create():
    """任务3: 创建子任务（有界并发池执行，独立沙箱 + git 基线）"""
    _stc = request.json or {}
    _stc_uid = _stc.get("user_id", "default")
    _stc_sid = _stc.get("session_id", "default")
    _stc_spec = _stc.get("task_spec") or _stc.get("message") or ""
    # dict 兼容：task_spec 是对象时提取 task 字段或序列化
    if isinstance(_stc_spec, dict):
        _stc_spec = _stc_spec.get("task") or json.dumps(_stc_spec, ensure_ascii=False)
    _stc_spec = str(_stc_spec).strip()
    if not _stc_spec:
        return _missing("task_spec")
    from core.gateway.subtask_executor import SubtaskDepthError, resolve_depth, submit

    # 委托深度预算: 请求传父深度(depth), 子任务深度=父+1; 超 maxDepth(默认 3) 拒绝
    _stc_parent_depth = int(_stc.get("depth", 0) or 0)
    _stc_depth = resolve_depth(_stc_parent_depth)
    try:
        _stc_tid = submit(_stc_uid, _stc_sid, _stc_spec, _stc.get("model", "deepseek-v4-flash"), depth=_stc_depth)
    except SubtaskDepthError as _stc_de:
        return jsonify(
            {
                "success": False,
                "error": str(_stc_de),
                "error_code": "SUBTASK_DEPTH_EXCEEDED",
                "depth": _stc_depth,
                "max_depth": _stc_de.max_depth,
            }
        )
    return jsonify(
        {
            "success": True,
            "task_id": _stc_tid,
            "status": "queued",
            "depth": _stc_depth,
            "message": "子任务已提交，有界并发池执行",
        }
    )


@bp.route("/v9/subtask/status", methods=["GET"])
def v9_subtask_status():
    """任务3: 查询子任务状态列表（前端卡片轮询）"""
    _sts = request.args or {}
    # ⭐ PM 2026-10-04（承 技总 954 §一 · PM-011 N11）：缺键 ⛔ 静默落 default
    #   —— 否则「缺键」与「真无件」同形 ⇒ 量具/用户误判（派活演示批即栽此）。
    if not _sts.get("user_id"):
        return _missing("user_id")
    if not _sts.get("session_id"):
        return _missing("session_id")
    _sts_uid = _sts.get("user_id")
    _sts_sid = _sts.get("session_id")
    from core.gateway.subtask_executor import list_subtasks

    return jsonify({"success": True, "subtasks": list_subtasks(_sts_uid, _sts_sid)})


@bp.route("/v9/subtask/stop", methods=["POST"])
def v9_subtask_stop():
    """⭐ T2-刀8 §五：**置标志**之停止／撤回（`mode ∈ cancel|withdraw` · ⛔ 硬杀）。"""
    _sp = request.json or {}
    if not _sp.get("user_id"):
        return _missing("user_id")
    if not _sp.get("session_id"):
        return _missing("session_id")
    if not _sp.get("task_id"):
        return _missing("task_id")
    from core.gateway.subtask_executor import stop

    r = stop(
        _sp.get("user_id"),
        _sp.get("session_id"),
        _sp.get("task_id"),
        mode=_sp.get("mode") or "cancel",
        by=_sp.get("by") or "",
        reason=_sp.get("reason") or "",
    )
    return jsonify(r) if r.get("ok") else (jsonify(r), 400)


@bp.route("/v9/subtask/resume", methods=["POST"])
def v9_subtask_resume():
    """⭐ T2-刀8 §五：**断点续** —— 重投 `interrupted` 件（⛔ 续无全规格者）。"""
    _rp = request.json or {}
    if not _rp.get("user_id"):
        return _missing("user_id")
    if not _rp.get("session_id"):
        return _missing("session_id")
    from core.gateway.subtask_executor import resume

    return jsonify(
        resume(
            _rp.get("user_id"),
            _rp.get("session_id"),
            task_id=_rp.get("task_id"),
            model=_rp.get("model") or "deepseek-v4-flash",
        )
    )


@bp.route("/v9/goal/history", methods=["GET"])
def v9_goal_history():
    """P2 跨 session 复盘: 该用户所有 session 的 goal 列表(含 progress/status/时间 + 最近 turn 摘要)。

    复用 list_goals(user_id) + get_session_log(sid).derive_turns()。
    """
    _gh = request.args or {}
    _gh_uid = _gh.get("user_id", "default")
    _gh_limit = int(_gh.get("limit", 100) or 100)
    try:
        from core.gateway.goal_state import list_goals
        from core.gateway.session_log import get_session_log

        _gh_goals = list_goals(_gh_uid, limit=_gh_limit) or []
        _gh_out = []
        for _g in _gh_goals:
            _item = {
                "goal_id": _g.get("goal_id", ""),
                "session_id": _g.get("session_id", ""),
                "objective": str(_g.get("objective", ""))[:300],
                "status": _g.get("status", ""),
                "progress": _g.get("progress") or {},
                "started_at": _g.get("started_at", 0),
                "updated_at": _g.get("updated_at", 0),
                "source_turn": _g.get("source_turn"),
                # 报告持久化: 任务最终报告(旧 goal 无此字段 → 空串, 前端按空处理)
                "report": str(_g.get("report") or "")[:8000],
            }
            # turns 并入(减少往返): 复用 derive_turns, 带该 goal 相关的最近 turn 摘要
            try:
                _g_sid = _item["session_id"] or _gh_uid
                _turns = get_session_log(_g_sid).derive_turns()
                _recent = []
                for _t in _turns[-5:]:
                    _recent.append(
                        {
                            "turn_id": _t.get("turn_id"),
                            "reason": _t.get("reason", ""),
                            "reason_detail": str(_t.get("reason_detail", ""))[:120],
                            "tools": sum(len(_s.get("tools", [])) for _s in _t.get("steps", [])),
                            "tokens": _t.get("tokens", 0),
                            "started_at": _t.get("started_at", 0),
                        }
                    )
                _item["turns"] = _recent
                # 最近一次 turn 的 reason(未完成任务的真实结束原因: error/paused/max_tokens...)
                _last_rs = ""
                for _t in reversed(_recent):
                    if _t.get("reason"):
                        _last_rs = _t["reason"]
                        break
                _item["last_reason"] = _last_rs
            except Exception:
                _item["turns"] = []
                _item["last_reason"] = ""
            _gh_out.append(_item)
        return jsonify({"success": True, "goals": _gh_out})
    except Exception as _gh_err:
        return jsonify({"success": False, "error": str(_gh_err)[:300]})


@bp.route("/v9/session/clean", methods=["POST"])
def v9_session_clean():
    """清理会话上下文：messages 快照 / _pending_writes / _plan_pending / goal

    供前端"清空对话"按钮调用（V8 频道 + V9 工作区共用）。
    只清会话状态，不删除用户文件。
    """
    from core.gateway.session_cleaner import _clean_session_context

    _cl = request.json or {}
    _cl_uid = _cl.get("user_id", "default")
    _cl_sid = _cl.get("session_id", "default")
    _clean_session_context(_cl_uid, _cl_sid)
    return jsonify({"success": True, "message": "会话上下文已清理"})


@bp.route("/api/v5/session/create", methods=["POST"])
def session_create():
    import uuid

    from core.lib.session_manager import session_manager

    data = request.json or {}
    user_id = data.get("user_id", "default")
    session_id = str(uuid.uuid4())[:8]
    session_manager.get_or_create(session_id, user_id)
    return jsonify({"success": True, "session_id": session_id})


@bp.route("/api/v5/session/list", methods=["GET"])
def session_list():
    from core.lib.session_manager import session_manager

    user_id = request.args.get("user_id", "default")
    return jsonify({"success": True, "sessions": session_manager.list_sessions(user_id)})
