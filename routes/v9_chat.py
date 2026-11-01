"""/v9/agent 路由：旧 chat 兼容 ＋ /v9/agent/runs 异步执行 API（P0-2c）。

旧 /v9/agent/chat 语义不变：仍直调 run_chat_entry（同步/SSE）。
新增 /v9/agent/runs 4 端点：接全局 RunService（单 worker），
runner 先接现有 run_chat_entry；本文件不 import DSH/不建第二 worker。
"""

import os
import threading
import uuid

from flask import Blueprint, Response, jsonify, request, stream_with_context

bp = Blueprint("v9_chat_routes", __name__)
_deps = {}

# P2-4：多席顺序编排（task 前缀承载 seats；⛔ 改 queue schema）
MULTI_SEAT_PREFIX = "【多席编排】seats="
MAX_SEATS = 3
SEAT_ROLES = {
    "PM": "你是 PM（产品）。负责产品方向、用户价值、范围与优先级裁决；给出明确的取舍理由与验收边界。",
    "PD": "你是 PD（技术）。负责技术方案、架构、依赖与可行性验证；指出风险、替代方案与落地步骤。",
    "CW": "你是 CW（文案/内容）。负责文案、表达、信息结构与交付物质量；输出可直接使用的成稿建议。",
    "TD": "你是 TD（测试/质量）。负责测试策略、质量门槛、回归范围与风险；给出可执行的验证清单。",
}

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
    # P0 产品面：审批续跑也归 runs 面（前端不再打 /v9/agent/chat）
    app.add_url_rule(
        "/v9/agent/runs/approval",
        view_func=v9_agent_runs_approval,
        methods=["POST"],
        endpoint="v9_agent_runs_approval",
    )


# ---------------- 旧 chat（语义不变） ----------------


def v9_agent_chat():
    """代理 DeepSeek API 调用，前端不暴露 Key。"""
    from core.gateway.v9_chat.entry import run_chat_entry

    payload, kind = run_chat_entry(data=request.json or {}, deps=_deps)
    if kind == "stream":
        return Response(stream_with_context(payload), mimetype="text/event-stream")
    return jsonify(payload)


def v9_agent_runs_approval():
    u"""审批续跑：复用既有 run_chat_entry 的 approve_write 语义，但归 runs 面。

    产品前端只打 /v9/agent/runs/approval；旧 /v9/agent/chat 保留兼容，不再由产品发送链使用。
    """
    from core.gateway.v9_chat.entry import run_chat_entry

    payload, kind = run_chat_entry(data=request.json or {}, deps=_deps)
    if kind == "stream":
        # 审批结果应为非流；若后端仍返流，按 SSE 交回，前端可照旧读取。
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


def _normalize_seats(raw):
    """去重/大写/限 3 席，仅 PM/PD/CW/TD。"""
    out = []
    if isinstance(raw, (list, tuple)):
        for item in raw:
            seat = str(item or "").strip().upper()
            if seat in SEAT_ROLES and seat not in out:
                out.append(seat)
                if len(out) >= MAX_SEATS:
                    break
    return out


def _split_multi_task(task):
    """解析 task 前缀；返回 (seats, 原 task)，非多席 ⇒ ([], task)。"""
    text = str(task or "")
    if not text.startswith(MULTI_SEAT_PREFIX):
        return [], text
    head, sep, body = text.partition("\n")
    if not sep:
        return [], text
    seats = _normalize_seats(head[len(MULTI_SEAT_PREFIX) :].split(","))
    return seats, body


def _ollama_content(got):
    try:
        return str(((got.get("data") or {}).get("choices") or [{}])[0].get("message", {}).get("content") or "")
    except Exception:  # noqa: BLE001
        return ""


def _run_multi_seats(ollama, model, seats, task):
    """顺序每席本地 Ollama（角色 system prompt）→ 一次综合 prompt。"""
    seat_results = []
    for seat in seats:
        messages = [{"role": "system", "content": SEAT_ROLES[seat]}, {"role": "user", "content": task}]
        try:
            got = ollama(messages=messages, tools=[], model=model, temperature=0.7, max_tokens=1500)
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "failed",
                "error": f"multi-seat {seat}: {type(exc).__name__}: {str(exc)[:300]}",
                "reason": "runner_multi_seat_failed",
            }
        if not isinstance(got, dict) or got.get("success") is not True:
            err = got.get("error") if isinstance(got, dict) else "non-dict result"
            return {
                "status": "failed",
                "error": f"multi-seat {seat}: {str(err or 'seat failed')[:300]}",
                "reason": "runner_multi_seat_failed",
            }
        seat_results.append({"seat": seat, "content": _ollama_content(got)})
    blocks = "\n\n".join(f"【{r['seat']}】{r['content']}" for r in seat_results)
    synth = (
        "你是多席编排的综合者。以下是各席对同一任务的意见；请消解冲突、保留关键理由，"
        "输出一份可直接执行的最终答复（不要逐席复述）。\n\n【原始任务】" + task + "\n\n【各席意见】\n" + blocks
    )
    try:
        got = ollama(
            messages=[
                {"role": "system", "content": "你是多席编排的综合者，负责给出最终统一答复。"},
                {"role": "user", "content": synth},
            ],
            tools=[],
            model=model,
            temperature=0.7,
            max_tokens=1500,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "failed",
            "error": f"multi-seat synthesis: {type(exc).__name__}: {str(exc)[:300]}",
            "reason": "runner_multi_seat_synthesis",
        }
    if not isinstance(got, dict) or got.get("success") is not True:
        err = got.get("error") if isinstance(got, dict) else "non-dict result"
        return {
            "status": "failed",
            "error": f"multi-seat synthesis: {str(err or 'synthesis failed')[:300]}",
            "reason": "runner_multi_seat_synthesis",
        }
    return {
        "status": "done",
        "output": {
            "ok": True,
            "content": _ollama_content(got),
            "seats": seat_results,
            "model": "multi-seat",
        },
        "error": "",
    }


def _dsh_run(task, timeout):
    """runs 之 DSH headless 分支：subprocess 调 dsh --profile headless（独立进程，⛔ Flask）。"""
    import shutil
    import subprocess

    exe = shutil.which("dsh") or "dsh"
    return subprocess.run(
        [exe, "--profile", "headless", str(task)],
        timeout=timeout,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


_RUN_CANCELS = {}


def _runner_cancel(run_id):
    """RunService 调 runner.cancel：置事件，让 Ollama 流式请求秒级收口。"""
    evt = _RUN_CANCELS.get(str(run_id))
    if evt is not None:
        evt.set()
        return True
    return False


def _run_localm(record, cancel_evt):
    """RunService 的 LocaLM 分支：OpenAI 流式 /v1/chat/completions，可取消。"""
    import json as _json
    import os as _os
    import requests as _rq

    model = str(record.get("model") or "")
    if model.startswith("localm:"):
        model = model.split(":", 1)[1]
    base = _os.getenv("LOCALM_BASE_URL", "http://127.0.0.1:8642").rstrip("/")
    headers = {}
    key = _os.getenv("LOCALM_API_KEY", "")
    if key:
        headers["Authorization"] = "Bearer " + key
    body = {
        "model": model,
        "messages": [{"role": "user", "content": str(record.get("task") or "")}],
        "stream": True,
        "max_tokens": 2000,
    }
    try:
        resp = _rq.post(base + "/v1/chat/completions", json=body, headers=headers, timeout=(10, 180), stream=True)
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "error": f"localm spawn: {type(exc).__name__}: {str(exc)[:300]}", "reason": "runner_localm_spawn"}
    if resp.status_code != 200:
        return {"status": "failed", "error": f"localm HTTP {resp.status_code}: {resp.text[:300]}", "reason": "runner_localm_http"}
    parts = []
    try:
        for raw in resp.iter_lines():
            if cancel_evt.is_set():
                try:
                    resp.close()
                except Exception:
                    pass
                return {"status": "cancelled", "output": {"ok": False, "content": "".join(parts)}, "error": "user_cancel", "reason": "user_cancel"}
            if not raw:
                continue
            line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
            if not line.startswith("data: "):
                continue
            data = line[6:].strip()
            if data == "[DONE]":
                break
            try:
                ev = _json.loads(data)
            except Exception:
                continue
            for ch in ev.get("choices") or []:
                delta = ch.get("delta") or {}
                if delta.get("content"):
                    parts.append(str(delta["content"]))
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "error": f"localm stream: {type(exc).__name__}: {str(exc)[:300]}", "reason": "runner_localm_stream"}
    finally:
        try:
            resp.close()
        except Exception:
            pass
    if cancel_evt.is_set():
        return {"status": "cancelled", "output": {"ok": False, "content": "".join(parts)}, "error": "user_cancel", "reason": "user_cancel"}
    return {"status": "done", "output": {"ok": True, "content": "".join(parts), "model": "localm:" + model}, "error": ""}


def _chat_entry_runner(record):
    """runner：本地 Ollama 直调 ＋ DSH headless 子进程（⛔ /v9/agent/chat、⛔ Flask request）。

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
    import threading as _th
    _cancel_evt = _RUN_CANCELS.get(str(record.get("run_id") or ""))
    if _cancel_evt is None:
        _cancel_evt = _th.Event()
        _RUN_CANCELS[str(record.get("run_id") or "")] = _cancel_evt
    model_in = str(record.get("model") or "").strip()
    if model_in.startswith("localm:"):
        return _run_localm(record, _cancel_evt)
    # P2-1：model=dsh/dsh-headless ⇒ 独立 DSH headless 子进程（本地 model 仍走 Ollama）
    if model_in.lower().startswith("dsh"):
        import subprocess as _sp

        timeout = float(record.get("timeout") or 180.0)
        try:
            proc = _dsh_run(str(record.get("task") or ""), timeout)
        except _sp.TimeoutExpired:
            return {
                "status": "failed",
                "error": f"dsh timeout after {timeout}s",
                "reason": "runner_dsh_timeout",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "failed",
                "error": f"dsh spawn: {type(exc).__name__}: {str(exc)[:300]}",
                "reason": "runner_dsh_spawn",
            }
        stdout = str(proc.stdout or "")
        stderr = str(proc.stderr or "")
        if proc.returncode == 0:
            return {
                "status": "done",
                "output": {"ok": True, "content": stdout, "model": "dsh-headless"},
                "error": "",
            }
        return {
            "status": "failed",
            "error": f"dsh rc={proc.returncode}: {(stderr or stdout)[:300]}",
            "reason": "runner_dsh_failed",
            "output": {"returncode": proc.returncode, "stdout": stdout[:1000], "stderr": stderr[:1000]},
        }
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
    seats, base_task = _split_multi_task(str(record.get("task") or ""))
    if len(seats) >= 2:
        return _run_multi_seats(_ollama_execute_with_tools, model, seats, base_task)
    # 单席/无 seats ⇒ 原单次路（单席仅剥前缀，不触发多席综合）
    single_task = base_task if seats else str(record.get("task") or "")
    messages = [{"role": "user", "content": single_task}]
    try:
        got = _ollama_execute_with_tools(messages=messages, tools=[], model=model, temperature=0.7, max_tokens=2000, cancel_event=_cancel_evt)
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
    seats = _normalize_seats(p.get("seats"))
    if seats:
        # 多席编排：仅以 task 前缀承载，queue schema 不变
        task = MULTI_SEAT_PREFIX + ",".join(seats) + "\n" + task
    model_in = str(p.get("model") or "").strip()
    # P2-2：DSH 无 DEEPSEEK_API_KEY ⇒ fail-fast 400（⛔ 不入队、⛔ 不跑必然失败）
    if model_in.lower().startswith("dsh") and not os.environ.get("DEEPSEEK_API_KEY"):
        return jsonify({"ok": False, "error": "dsh_requires_key", "code": "dsh_requires_key"}), 400
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


_chat_entry_runner.cancel = _runner_cancel


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
