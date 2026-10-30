"""task-164：_chat_entry_runner 本地 Ollama ＋ DSH headless 之测（fake，不真跑模型）.

覆盖：local success→done、failure→failed、remote→runner_remote_not_wired、异常→failed；
DSH fake 成功/失败/超时、model=dsh POST 202→done、真实 dsh 一句话（integration）；
/v9/agent/runs 202→done/cancel→cancelled。
"""

import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

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


def test_runner_multi_seat_two_plus_synthesis(monkeypatch):
    calls = []

    def _fake(**kw):
        calls.append(kw)
        if len(calls) == 1:
            return _ok("PM 意见")
        if len(calls) == 2:
            return _ok("PD 意见")
        return _ok("综合答复")

    monkeypatch.setattr(EAT, "_ollama_execute_with_tools", _fake)
    task = "【多席编排】seats=PM,PD\n做一个决定"
    got = API._chat_entry_runner(_record(task=task))
    assert got["status"] == "done", got
    assert got["output"]["model"] == "multi-seat"
    assert got["output"]["content"] == "综合答复"
    assert got["output"]["seats"] == [
        {"seat": "PM", "content": "PM 意见"},
        {"seat": "PD", "content": "PD 意见"},
    ]
    assert len(calls) == 3, "2 席 + 1 综合"
    assert calls[0]["messages"][0]["role"] == "system" and "PM" in calls[0]["messages"][0]["content"]
    assert calls[1]["messages"][0]["role"] == "system" and "PD" in calls[1]["messages"][0]["content"]
    assert "综合者" in calls[2]["messages"][0]["content"]


def test_runner_multi_seat_failure_is_explicit(monkeypatch):
    calls = []

    def _fake(**kw):
        calls.append(kw)
        if len(calls) == 1:
            return _ok("PM 意见")
        return {"success": False, "error": "PD down"}

    monkeypatch.setattr(EAT, "_ollama_execute_with_tools", _fake)
    got = API._chat_entry_runner(_record(task="【多席编排】seats=PM,PD\n做"))
    assert got["status"] == "failed"
    assert got["reason"] == "runner_multi_seat_failed"
    assert "PD down" in got["error"]
    assert len(calls) == 2


def test_runner_single_seat_keeps_normal_path(monkeypatch):
    calls = []

    def _fake(**kw):
        calls.append(kw)
        return _ok("单席答")

    monkeypatch.setattr(EAT, "_ollama_execute_with_tools", _fake)
    got = API._chat_entry_runner(_record(task="【多席编排】seats=PM\n做"))
    assert got["status"] == "done"
    assert got["output"]["content"] == "单席答"
    assert "seats" not in got["output"]
    assert len(calls) == 1
    assert calls[0]["messages"] == [{"role": "user", "content": "做"}]


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


def test_runner_dsh_done(monkeypatch):
    calls = []

    def _fake(task, timeout):
        calls.append((task, timeout))
        return SimpleNamespace(returncode=0, stdout="dsh ok\n", stderr="")

    monkeypatch.setattr(API, "_dsh_run", _fake)
    got = API._chat_entry_runner(_record(model="dsh", task="一句话", timeout=10))
    assert got["status"] == "done" and got["error"] == ""
    assert got["output"]["content"] == "dsh ok\n"
    assert got["output"]["model"] == "dsh-headless"
    assert calls == [("一句话", 10.0)]


def test_runner_dsh_failed(monkeypatch):
    monkeypatch.setattr(
        API,
        "_dsh_run",
        lambda task, timeout: SimpleNamespace(returncode=2, stdout="", stderr="bad dsh"),
    )
    got = API._chat_entry_runner(_record(model="dsh-headless"))
    assert got["status"] == "failed"
    assert got["reason"] == "runner_dsh_failed" and "bad dsh" in got["error"]


def test_runner_dsh_timeout(monkeypatch):
    def _timeout(task, timeout):
        raise subprocess.TimeoutExpired(["dsh"], timeout)

    monkeypatch.setattr(API, "_dsh_run", _timeout)
    got = API._chat_entry_runner(_record(model="dsh", timeout=1))
    assert got["status"] == "failed"
    assert got["reason"] == "runner_dsh_timeout" and "timeout" in got["error"]


def test_runs_api_dsh_202_to_done(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(
        API,
        "_dsh_run",
        lambda task, timeout: SimpleNamespace(returncode=0, stdout="dsh api ok\n", stderr=""),
    )
    client, svc = _api(tmp_path, monkeypatch)
    try:
        r = client.post(
            "/v9/agent/runs",
            json={"user_id": "u", "session_id": "s", "task": "一句话", "timeout": 10, "model": "dsh"},
        )
        assert r.status_code == 202, r.get_data(as_text=True)
        rid = r.get_json()["run_id"]
        assert _wait(lambda: (client.get("/v9/agent/runs/" + rid).get_json() or {}).get("state") == "done")
        d = client.get("/v9/agent/runs/" + rid).get_json()
        assert d["state"] == "done" and d["ok"] is True
        assert d["output"]["content"] == "dsh api ok\n"
        assert d["output"]["model"] == "dsh-headless"
    finally:
        svc.stop(cancel_queued=False)
        API.reset_run_service()


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("dsh") is None, reason="dsh 不在 PATH")
def test_runner_dsh_real_one_sentence():
    """真实 dsh --profile headless：一句话返回非空。"""
    got = API._chat_entry_runner(_record(model="dsh", task="只回复：收到", timeout=180))
    assert got["status"] == "done", got
    assert str((got.get("output") or {}).get("content") or "").strip(), got


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("dsh") is None, reason="dsh 不在 PATH")
def test_runs_api_dsh_real_202_to_done(tmp_path, monkeypatch):
    """真实 dsh：POST /v9/agent/runs（model=dsh）202→done，content 非空。

    无真实 key 时 skip（P2-2 的 400 闸会先拦；直调真实 dsh 另有 integration 测）。
    """
    import os

    if not os.environ.get("DEEPSEEK_API_KEY"):
        pytest.skip("真实 dsh API 需 DEEPSEEK_API_KEY（否则 400 fail-fast）")
    client, svc = _api(tmp_path, monkeypatch)
    try:
        r = client.post(
            "/v9/agent/runs",
            json={"user_id": "u", "session_id": "s", "task": "只回复：收到", "timeout": 180, "model": "dsh"},
        )
        assert r.status_code == 202, r.get_data(as_text=True)
        rid = r.get_json()["run_id"]
        assert _wait(
            lambda: (client.get("/v9/agent/runs/" + rid).get_json() or {}).get("state") in ("done", "failed"),
            timeout=180,
            interval=0.2,
        )
        d = client.get("/v9/agent/runs/" + rid).get_json()
        assert d["state"] == "done", d
        assert str((d.get("output") or {}).get("content") or "").strip(), d
    finally:
        svc.stop(cancel_queued=False)
        API.reset_run_service()


@pytest.mark.integration
def test_runs_api_multi_seat_real_pm_pd(tmp_path, monkeypatch):
    """真实 seats=[PM,PD]：POST 202→done，output.seats 长度 2，内容非空。"""
    monkeypatch.setattr(EAT, "_ollama_execute_with_tools", EAT._ollama_execute_with_tools)
    client, svc = _api(tmp_path, monkeypatch)
    try:
        r = client.post(
            "/v9/agent/runs",
            json={
                "user_id": "u",
                "session_id": "s",
                "task": "用一句话给出结论：先交付还是先重构？",
                "timeout": 240,
                "model": "qwen2.5:7b-instruct-q4_0-gpu",
                "seats": ["PM", "PD"],
            },
        )
        assert r.status_code == 202, r.get_data(as_text=True)
        rid = r.get_json()["run_id"]
        assert _wait(
            lambda: (client.get("/v9/agent/runs/" + rid).get_json() or {}).get("state") in ("done", "failed"),
            timeout=240,
            interval=0.2,
        )
        d = client.get("/v9/agent/runs/" + rid).get_json()
        assert d["state"] == "done", d
        out = d["output"]
        assert out["model"] == "multi-seat"
        assert [s["seat"] for s in out["seats"]] == ["PM", "PD"]
        assert str(out["content"] or "").strip(), d
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
