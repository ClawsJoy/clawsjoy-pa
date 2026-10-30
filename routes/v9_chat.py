"""/v9/agent 路由：旧 chat 兼容 ＋ /v9/agent/runs 异步执行 API（P0-2c）。

旧 /v9/agent/chat 语义不变：仍直调 run_chat_entry（同步/SSE）。
新增 /v9/agent/runs 4 端点：接全局 RunService（单 worker），
runner 先接现有 run_chat_entry；本文件不 import DSH/不建第二 worker。
"""

import threading
import uuid

from flask import Blueprint, Response, jsonify, request, stream_with_context

bp = Blueprint("v9_chat_routes", __name__)
_deps = {}

_run_service = None
_run_service_lock = threading.Lock()


def register(app, *, bridge_loop_fn, allowed_commands, max_context_tokens, deepseek_key_loaded, resolve_session_id_fn):
    """注入 main 内部依赖后注册路由（防循环 import）。"""
    _deps.update(
        bridge_loop_fn=bridge_loop_fn,
        allowed_commands=allowed_commands,
        max_context_tokens=max_context_tokens,
        deepseek_key_loaded=deepseek_key_loaded,
        resolve_session_id_fn=resolve_session_id_fn,
    )
    app.add_url_rule("/v9/agent/chat", view_func=v9_agent_chat, methods=["POST"], endpoint="v9_agent_chat")
    # P0-2c：异步执行 API（不新建路由文件）
    app.add_url_rule("/v9/agent/runs", view_func=v9_agent_runs_post, methods=["POST"], endpoint="v9_agent_runs_post")
    app.add_url_rule("/v9/agent/runs", view_func=v9_agent_runs_list, methods=["GET"], endpoint="v9_agent_runs_list")
    app.add_url_rule(
        "/v9/agent/runs/<run_id>", view_func=v9_agent_run_get, methods=["GET"], endpoint="v9_agent_run_get"
    )
    app.add_url_rule(
        "/v9/agent/runs/<run_id>/cancel",
        view_func=v9_agent_run_cancel,
        methods=["POST"],
        endpoint="v9_agent_run_cancel",
    )


# ---------------- 旧 chat（语义不变） ----------------


def v9_agent_chat():
    """代理 DeepSeek API 调用，前端不暴露 Key。"""
    from core.gateway.v9_chat.entry import run_chat_entry

    payload, kind = run_chat_entry(data=request.json or {}, deps=_deps)
    if kind == "stream":
        return Response(stream_with_context(payload), mimetype="text/event-stream")
    return jsonify(payload)


# ---------------- 全局 RunService（单 worker） ----------------


def configure_run_service(service):
    """测试/宿主注入 RunService（生产用 _get_run_service 懒建）。"""
    global _run_service
    with _run_service_lock:
        _run_service = service
    return service


def reset_run_service():
    global _run_service
    with _run_service_lock:
        old, _run_service = _run_service, None
    return old


def _get_run_service():
    global _run_service
    with _run_service_lock:
        if _run_service is not None:
            return _run_service
        from core.pa.run_queue import AsyncRunQueue
        from core.pa.run_service import RunService

        _run_service = RunService(queue=AsyncRunQueue(), runner=_chat_entry_runner, auto_start=True)
        return _run_service


def _chat_entry_runner(record):
    """runner：进程内直调本地 Ollama（⛔ /v9/agent/chat、⛔ subprocess、⛔ Flask request）。

    病：subprocess/HTTP 回调同进程 Flask 仍会自阻塞，run 卡 running。
    修：RunService worker 直接调 execute_agent_task._ollama_execute_with_tools（tools=[]）；
    model 取 provider_route.route_for_model；仅 local 可跑，remote/非 local 明确 failed
    runner_remote_not_wired。旧 /v9/agent/chat 语义不变。
    """
    try:
        from core.gateway.execute_agent_task import _ollama_execute_with_tools
        from core.gateway.v9_chat.provider_route import route_for_model
        from core.pa import providers as _prov
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "failed",
            "error": f"runner import: {type(exc).__name__}: {str(exc)[:300]}",
            "reason": "runner_import",
        }
    model_in = str(record.get("model") or "").strip()
    try:
        route, _note = route_for_model(model_in)
        kind = _prov.route_kind(route)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "failed",
            "error": f"runner route: {type(exc).__name__}: {str(exc)[:300]}",
            "reason": "runner_route",
        }
    if kind != "local":
        return {
            "status": "failed",
            "error": "runner_remote_not_wired",
            "reason": "runner_remote_not_wired",
            "output": {"route": route, "kind": kind},
        }
    model = str(route.get("model") or model_in)
    messages = [{"role": "user", "content": str(record.get("task") or "")}]
    try:
        got = _ollama_execute_with_tools(messages=messages, tools=[], model=model, temperature=0.7, max_tokens=2000)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "failed",
            "error": f"local ollama: {type(exc).__name__}: {str(exc)[:300]}",
            "reason": "runner_local_exception",
        }
    if not isinstance(got, dict):
        return {"status": "failed", "error": "local ollama: non-dict result", "reason": "runner_local_output"}
    if got.get("success") is True:
        content = ""
        try:
            content = str(((got.get("data") or {}).get("choices") or [{}])[0].get("message", {}).get("content") or "")
        except Exception:  # noqa: BLE001
            content = ""
        return {
            "status": "done",
            "output": {"ok": True, "content": content, "model": model, "route": route},
            "error": "",
        }
    return {
        "status": "failed",
        "output": got,
        "error": str(got.get("error") or "local ollama failed")[:300],
        "reason": "runner_local_failed",
    }


# ---------------- API：4 端点 ----------------


def v9_agent_runs_post():
    """POST /v9/agent/runs：受理即回 run_id/state/position（忙 ⇒ queued，⛔ 409）。"""
    from core.pa.run_queue import QueueFull

    p = request.get_json(silent=True) or {}
    task = str(p.get("task") or "").strip()
    if not task:
        for m in reversed(p.get("messages") or []):
            if isinstance(m, dict) and m.get("role") == "user":
                task = str(m.get("content") or "").strip()
                break
    if not task:
        return jsonify({"ok": False, "error": "task_required", "code": "bad_request"}), 400
    cid = str(p.get("client_request_id") or "").strip() or uuid.uuid4().hex
    svc = _get_run_service()
    try:
        rec = svc.submit(
            session_id=str(p.get("session_id") or "default"),
            user_id=str(p.get("user_id") or "default"),
            client_request_id=cid,
            task=task,
            model=str(p.get("model") or ""),
            permission_level=str(p.get("permission_level") or ""),
            cwd=str(p.get("cwd") or ""),
            timeout=float(p.get("timeout") or 0.0),
        )
    except QueueFull as exc:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "queue_full",
                    "code": "queue_full",
                    "session_queued": exc.session_queued,
                    "global_queued": exc.global_queued,
                }
            ),
            429,
        )
    except (TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)[:300], "code": "bad_request"}), 400
    cur = svc.get(rec["run_id"])
    return (
        jsonify(
            {
                "ok": True,
                "run_id": cur["run_id"],
                "state": cur["state"],
                "position": cur.get("position", 0),
                "queue_depth": svc.snapshot().get("queue_depth", 0),
                "client_request_id": cur.get("client_request_id"),
            }
        ),
        202,
    )


def v9_agent_runs_list():
    """GET /v9/agent/runs?session_id=&state=&limit=：队列/历史列表。"""
    svc = _get_run_service()
    state = request.args.get("state") or None
    session_id = request.args.get("session_id") or None
    try:
        limit = max(1, min(200, int(request.args.get("limit") or 50)))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "bad_limit", "code": "bad_request"}), 400
    runs = svc.queue.list_runs(state=state, session_id=session_id)[:limit]
    return jsonify({"ok": True, "runs": runs, "count": len(runs), "queue_depth": svc.snapshot().get("queue_depth", 0)})


def v9_agent_run_get(run_id):
    """GET /v9/agent/runs/<id>?after_seq=N：状态/进度/增量事件。"""
    from core.pa.run_queue import RunNotFound

    svc = _get_run_service()
    try:
        rec = svc.get(run_id)
    except RunNotFound:
        return jsonify({"ok": False, "error": "run_not_found", "code": "not_found", "run_id": run_id}), 404
    try:
        after = max(0, int(request.args.get("after_seq") or 0))
    except (TypeError, ValueError):
        after = 0
    events = [e for e in svc.events() if e.get("run_id") == run_id and int(e.get("seq") or 0) > after]
    next_seq = max([int(e.get("seq") or 0) for e in events] or [after])
    out = dict(rec)
    out.update({"ok": True, "events": events, "next_after_seq": next_seq})
    return jsonify(out)


def v9_agent_run_cancel(run_id):
    """POST /v9/agent/runs/<id>/cancel：queued 立即取消；running 置 flag＋runner.cancel。"""
    from core.pa.run_queue import RunNotFound

    svc = _get_run_service()
    p = request.get_json(silent=True) or {}
    try:
        rec = svc.cancel(run_id, reason=str(p.get("reason") or "user_cancel"))
    except RunNotFound:
        return jsonify({"ok": False, "error": "run_not_found", "code": "not_found", "run_id": run_id}), 404
    closed = _close_turn_registry(rec.get("session_id") or "")
    return jsonify(
        {
            "ok": True,
            "run_id": run_id,
            "state": rec.get("state"),
            "cancel_requested": bool(rec.get("cancel_requested")),
            "turn_registry_closed": closed,
        }
    )


def _close_turn_registry(session_id):
    """取消时同步关该 session 的非终态 turn（承 routes/session.py 的修）。"""
    if not session_id:
        return []
    try:
        from core.gateway import turn_registry as tr

        closed = []
        for t in tr.list_turns(session_id=session_id, limit=50):
            if t.get("status") in ("CREATED", "RUNNING", "DETACHED"):
                if tr.finish_turn(t["turn_key"], "CANCELLED", "user_stop"):
                    closed.append(t["turn_key"])
        return closed
    except Exception:  # noqa: BLE001
        return []
