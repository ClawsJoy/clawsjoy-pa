"""task-152：_chat_entry_runner 直调本地 Ollama 之测（fake，不真跑模型）.

覆盖：local success→done、failure→failed、remote→runner_remote_not_wired、
异常→failed；/v9/agent/runs 202→done/cancel→cancelled（fake ollama）。
"""

import sys
import threading
import time
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import core.gateway.execute_agent_task as EAT  # noqa: E402
import routes.v9_chat as API  # noqa: E402
from core.pa.run_queue import AsyncRunQueue  # noqa: E402
from core.pa.run_service import RunService  # noqa: E402


def _ok(data_text="local ok"):
    return {"success": True, "data": {"choices": [{"message": {"content": data_text}}]}, "tokens": 3}


def _record(model="qwen2.5:7b-instruct-q4_0-gpu", task="hi", timeout=5.0):
    return {"user_id": "u", "session_id": "s", "model": model, "task": task, "timeout": timeout}


def _wait(predicate, timeout=5.0, interval=0.01):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(interval)
    return False


def test_runner_local_done(monkeypatch):
    calls = []

    def _fake(**kw):
        calls.append(kw)
        return _ok()

    monkeypatch.setattr(EAT, "_ollama_execute_with_tools", _fake)
    got = API._chat_entry_runner(_record())
    assert got["status"] == "done" and got["error"] == ""
    assert got["output"]["content"] == "local ok"
    assert calls and calls[0]["tools"] == []
    assert calls[0]["messages"] == [{"role": "user", "content": "hi"}]
    assert calls[0]["model"] == "qwen2.5:7b-instruct-q4_0-gpu"


def test_runner_local_failed(monkeypatch):
    monkeypatch.setattr(EAT, "_ollama_execute_with_tools", lambda **kw: {"success": False, "error": "ollama down"})
    got = API._chat_entry_runner(_record())
    assert got["status"] == "failed" and "ollama down" in got["error"]


def test_runner_remote_not_wired(monkeypatch):
    calls = []
    monkeypatch.setattr(EAT, "_ollama_execute_with_tools", lambda **kw: calls.append(kw) or _ok())
    got = API._chat_entry_runner(_record(model="deepseek-v4-flash"))
    assert got["status"] == "failed"
    assert got["error"] == "runner_remote_not_wired"
    assert got["reason"] == "runner_remote_not_wired"
    assert calls == [], "remote ⛔ 调本地 Ollama"


def test_runner_local_exception(monkeypatch):
    def _boom(**kw):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(EAT, "_ollama_execute_with_tools", _boom)
    got = API._chat_entry_runner(_record())
    assert got["status"] == "failed" and "RuntimeError" in got["error"]


# ---------- API：202→done / cancel→cancelled ----------


def _api(tmp_path, monkeypatch):
    q = AsyncRunQueue(path=tmp_path / "q.json")
    svc = RunService(queue=q, runner=API._chat_entry_runner, auto_start=True)
    API.configure_run_service(svc)
    monkeypatch.setattr(API, "_close_turn_registry", lambda sid: [])
    app = Flask(__name__)
    API.register(
        app,
        bridge_loop_fn=lambda *a, **k: None,
        allowed_commands=[],
        max_context_tokens=1000,
        deepseek_key_loaded="",
        resolve_session_id_fn=lambda uid, sid: (sid or "default", False),
    )
    return app.test_client(), svc


def test_runs_202_to_done(tmp_path, monkeypatch):
    monkeypatch.setattr(EAT, "_ollama_execute_with_tools", lambda **kw: _ok("runs done"))
    client, svc = _api(tmp_path, monkeypatch)
    try:
        r = client.post(
            "/v9/agent/runs",
            json={
                "user_id": "u",
                "session_id": "s",
                "task": "hi",
                "timeout": 5,
                "model": "qwen2.5:7b-instruct-q4_0-gpu",
            },
        )
        assert r.status_code == 202, r.get_data(as_text=True)
        rid = r.get_json()["run_id"]
        assert _wait(lambda: (client.get("/v9/agent/runs/" + rid).get_json() or {}).get("state") == "done")
        d = client.get("/v9/agent/runs/" + rid).get_json()
        assert d["state"] == "done" and d["ok"] is True
        assert d["output"]["content"] == "runs done"
    finally:
        svc.stop(cancel_queued=False)
        API.reset_run_service()


@pytest.mark.integration
def test_runs_real_local_ollama_done(tmp_path, monkeypatch):
    """真实本地 Ollama：runs 202→done（无 fake；需本机 11434）。"""
    client, svc = _api(tmp_path, monkeypatch)
    try:
        r = client.post(
            "/v9/agent/runs",
            json={
                "user_id": "u",
                "session_id": "s",
                "task": "只回复：收到",
                "timeout": 30,
                "model": "qwen2.5:7b-instruct-q4_0-gpu",
            },
        )
        assert r.status_code == 202, r.get_data(as_text=True)
        rid = r.get_json()["run_id"]
        assert _wait(
            lambda: (client.get("/v9/agent/runs/" + rid).get_json() or {}).get("state") in ("done", "failed"),
            timeout=30,
        )
        d = client.get("/v9/agent/runs/" + rid).get_json()
        assert d["state"] == "done", d
        assert str((d.get("output") or {}).get("content") or "").strip(), d
    finally:
        svc.stop(cancel_queued=False)
        API.reset_run_service()


def test_runs_cancel_to_cancelled(tmp_path, monkeypatch):
    started = threading.Event()
    gate = threading.Event()

    def _slow(**kw):
        started.set()
        gate.wait(4)
        return _ok()

    monkeypatch.setattr(EAT, "_ollama_execute_with_tools", _slow)
    client, svc = _api(tmp_path, monkeypatch)
    try:
        r = client.post(
            "/v9/agent/runs",
            json={
                "user_id": "u",
                "session_id": "s",
                "task": "hi",
                "timeout": 5,
                "model": "qwen2.5:7b-instruct-q4_0-gpu",
            },
        )
        assert r.status_code == 202
        rid = r.get_json()["run_id"]
        assert started.wait(4)
        c = client.post("/v9/agent/runs/" + rid + "/cancel", json={"reason": "stop"})
        assert c.status_code == 200 and c.get_json()["cancel_requested"] is True
        gate.set()
        assert _wait(lambda: (client.get("/v9/agent/runs/" + rid).get_json() or {}).get("state") == "cancelled")
    finally:
        svc.stop(cancel_queued=False)
        API.reset_run_service()
