"""/v9/agent/runs API 之测（task-147）：202/queued/position/query/cancel/404/幂等/queue_full.

用 fake runner，不真跑模型；test_client 不启动真实 chat。
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

import routes.v9_chat as API  # noqa: E402
from core.pa.run_queue import AsyncRunQueue  # noqa: E402
from core.pa.run_service import RunService  # noqa: E402


def _wait(predicate, timeout=4.0, interval=0.01):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(interval)
    return False


def _ok_runner(rec):
    return {"status": "done", "output": {"text": "ok:" + rec["run_id"]}}


class _Blocking:
    def __init__(self):
        self.started = threading.Event()
        self.gate = threading.Event()
        self.cancel_calls = []

    def __call__(self, rec):
        self.started.set()
        self.gate.wait(4)
        return {"status": "done", "output": {"text": "late"}}

    def cancel(self, run_id):
        self.cancel_calls.append(run_id)


@pytest.fixture()
def env_factory(tmp_path, monkeypatch):
    created = []
    closed = []
    monkeypatch.setattr(API, "_close_turn_registry", lambda sid: closed.append(sid) or [])

    def _make(runner, auto_start=False):
        q = AsyncRunQueue(path=tmp_path / f"q-{len(created)}.json")
        svc = RunService(queue=q, runner=runner, auto_start=auto_start)
        API.configure_run_service(svc)
        app = Flask(__name__)
        API.register(
            app,
            bridge_loop_fn=lambda *a, **k: None,
            allowed_commands=[],
            max_context_tokens=1000,
            deepseek_key_loaded="",
            resolve_session_id_fn=lambda uid, sid: (sid or "default", False),
        )
        created.append(svc)
        return app.test_client(), svc, closed

    yield _make
    for svc in created:
        svc.stop(cancel_queued=False)
    API.reset_run_service()


def _post(client, text="do it", **kw):
    body = {"user_id": "u", "session_id": "s1", "task": text}
    body.update(kw)
    return client.post("/v9/agent/runs", json=body)


# ---------- 受理 202 / queued / position ----------


def test_post_202_queued_position(env_factory):
    client, svc, _closed = env_factory(_ok_runner, auto_start=False)
    r = _post(client, client_request_id="c1")
    assert r.status_code == 202, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is True and d["state"] == "queued"
    assert d["position"] == 1 and d["queue_depth"] == 1
    assert d["run_id"] and d["client_request_id"] == "c1"
    svc.start()
    assert _wait(lambda: svc.get(d["run_id"])["state"] == "done")
    g = client.get("/v9/agent/runs/" + d["run_id"])
    assert g.status_code == 200
    assert g.get_json()["state"] == "done"


def test_busy_submit_queued_position(env_factory):
    runner = _Blocking()
    client, svc, _closed = env_factory(runner, auto_start=True)
    r1 = _post(client, "first", client_request_id="b1")
    assert r1.status_code == 202 and r1.get_json()["run_id"]
    assert runner.started.wait(4)
    r2 = _post(client, "second", client_request_id="b2")
    assert r2.status_code == 202, r2.get_data(as_text=True)
    d2 = r2.get_json()
    assert d2["state"] == "queued" and d2["position"] == 1
    assert svc.queue.queue_depth() == 1
    runner.gate.set()
    assert _wait(lambda: svc.get(d2["run_id"])["state"] == "done")


def test_idempotent_client_request_id(env_factory):
    client, svc, _closed = env_factory(_ok_runner, auto_start=False)
    a = _post(client, "same", client_request_id="same").get_json()
    b = _post(client, "same", client_request_id="same").get_json()
    assert a["run_id"] == b["run_id"]
    assert svc.queue.queue_depth() == 1
    assert len(svc.queue.list_runs()) == 1


def test_task_required_400(env_factory):
    client, _svc, _closed = env_factory(_ok_runner, auto_start=False)
    r = client.post("/v9/agent/runs", json={"user_id": "u", "session_id": "s"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "task_required"


def test_queue_full_429(env_factory):
    client, svc, _closed = env_factory(_ok_runner, auto_start=False)
    for i in range(3):
        r = _post(client, f"t{i}", client_request_id=f"q{i}")
        assert r.status_code == 202
    r = _post(client, "overflow", client_request_id="q-over")
    assert r.status_code == 429, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is False and d["error"] == "queue_full"
    assert d["session_queued"] == 3


# ---------- 查询 ----------


def test_get_after_seq_events(env_factory):
    client, svc, _closed = env_factory(_ok_runner, auto_start=True)
    rid = _post(client, "q", client_request_id="g1").get_json()["run_id"]
    assert _wait(lambda: svc.get(rid)["state"] == "done")
    d = client.get("/v9/agent/runs/" + rid).get_json()
    assert d["ok"] is True and d["state"] == "done"
    assert d["output"]["text"].startswith("ok:")
    assert d["events"], d
    first_seq = d["events"][0]["seq"]
    d2 = client.get("/v9/agent/runs/" + rid + "?after_seq=" + str(first_seq)).get_json()
    assert all(e["seq"] > first_seq for e in d2["events"])
    assert d2["next_after_seq"] >= first_seq


def test_get_404(env_factory):
    client, _svc, _closed = env_factory(_ok_runner, auto_start=False)
    r = client.get("/v9/agent/runs/nope")
    assert r.status_code == 404
    assert r.get_json()["error"] == "run_not_found"


def test_list_filter(env_factory):
    client, svc, _closed = env_factory(_ok_runner, auto_start=False)
    _post(client, "a", session_id="s1", client_request_id="l1")
    _post(client, "b", session_id="s2", client_request_id="l2")
    d = client.get("/v9/agent/runs?session_id=s1").get_json()
    assert d["ok"] is True and d["count"] == 1
    assert d["runs"][0]["session_id"] == "s1"
    d2 = client.get("/v9/agent/runs?state=queued").get_json()
    assert d2["count"] == 2 and d2["queue_depth"] == 2


# ---------- 取消 ----------


def test_cancel_queued_immediate(env_factory):
    client, svc, closed = env_factory(_ok_runner, auto_start=False)
    rid = _post(client, "x", session_id="sess", client_request_id="c1").get_json()["run_id"]
    r = client.post("/v9/agent/runs/" + rid + "/cancel", json={"reason": "user"})
    assert r.status_code == 200
    d = r.get_json()
    assert d["ok"] is True and d["state"] == "cancelled"
    assert d["cancel_requested"] is True
    assert closed == ["sess"], "取消须关 turn_registry"
    assert svc.queue.queue_depth() == 0


def test_cancel_running_flag_and_runner_cancel(env_factory):
    runner = _Blocking()
    client, svc, closed = env_factory(runner, auto_start=True)
    rid = _post(client, "x", session_id="sess", client_request_id="c2").get_json()["run_id"]
    assert runner.started.wait(4)
    r = client.post("/v9/agent/runs/" + rid + "/cancel", json={"reason": "stop"})
    assert r.status_code == 200
    d = r.get_json()
    assert d["state"] == "running" and d["cancel_requested"] is True
    assert runner.cancel_calls == [rid]
    assert closed == ["sess"]
    runner.gate.set()
    assert _wait(lambda: svc.get(rid)["state"] == "cancelled")


def test_cancel_404(env_factory):
    client, _svc, _closed = env_factory(_ok_runner, auto_start=False)
    r = client.post("/v9/agent/runs/nope/cancel", json={})
    assert r.status_code == 404
    assert r.get_json()["error"] == "run_not_found"


# ---------- 旧 chat 保持 ----------


def test_old_chat_route_kept(env_factory):
    client, _svc, _closed = env_factory(_ok_runner, auto_start=False)
    rules = {str(r.rule) for r in client.application.url_map.iter_rules()}
    assert "/v9/agent/chat" in rules
    assert "/v9/agent/runs" in rules and "/v9/agent/runs/<run_id>" in rules


# ---------- P2-4：seats 前缀（不改 queue schema） ----------


def test_post_seats_prefixes_task_dedup_max3(env_factory):
    client, svc, _closed = env_factory(_ok_runner, auto_start=False)
    r = _post(client, "原任务", seats=["PM", "PD", "PM", "TD", "CW"])
    assert r.status_code == 202, r.get_data(as_text=True)
    task = svc.queue.list_runs()[0]["task"]
    assert task == "【多席编排】seats=PM,PD,TD\n原任务", "去重/限 3/仅前缀承载，不改 schema"


def test_post_empty_or_invalid_seats_keeps_task(env_factory):
    client, svc, _closed = env_factory(_ok_runner, auto_start=False)
    r = _post(client, "原任务", seats=["XX", "PM"])
    assert r.status_code == 202
    assert svc.queue.list_runs()[0]["task"] == "【多席编排】seats=PM\n原任务"
    client2, svc2, _closed2 = env_factory(_ok_runner, auto_start=False)
    r2 = _post(client2, "原任务", seats=[])
    assert r2.status_code == 202
    assert svc2.queue.list_runs()[0]["task"] == "原任务"


# ---------- P2-2：DSH 无 key fail-fast ----------


def test_dsh_without_key_400_not_enqueued(env_factory, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client, svc, _closed = env_factory(_ok_runner, auto_start=False)
    r = _post(client, model="dsh")
    assert r.status_code == 400, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is False
    assert d["error"] == "dsh_requires_key" and d["code"] == "dsh_requires_key"
    assert "run_id" not in d
    assert svc.queue.list_runs() == [], "无 key ⛔ 建 run / ⛔ 入队"
    assert svc.snapshot()["queue_depth"] == 0


def test_dsh_headless_without_key_400(env_factory, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client, svc, _closed = env_factory(_ok_runner, auto_start=False)
    r = _post(client, model="dsh-headless")
    assert r.status_code == 400
    assert r.get_json()["code"] == "dsh_requires_key"
    assert svc.queue.list_runs() == []


def test_dsh_with_key_not_blocked(env_factory, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    client, svc, _closed = env_factory(_ok_runner, auto_start=False)
    r = _post(client, model="dsh")
    assert r.status_code == 202, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is True and d["state"] == "queued" and d["run_id"]
    assert len(svc.queue.list_runs()) == 1, "有 key ⇒ 正常入队（fake runner，不跑真 dsh）"
