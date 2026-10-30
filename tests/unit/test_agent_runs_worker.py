"""task-150：独立 subprocess worker / _chat_entry_runner 之测（本地假 chat，不真跑模型）.

覆盖：worker CLI 成功/失败、runner done/failed/timeout、/v9/agent/runs 202→done、
cancel→cancelled（subprocess 收口后 cancelled）。
"""

import json
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import routes.v9_chat as API  # noqa: E402
from core.pa.run_queue import AsyncRunQueue  # noqa: E402
from core.pa.run_service import RunService  # noqa: E402

WORKER = ROOT / "scripts" / "pa_run_worker.py"


class _State:
    mode = "success"
    delay = 0.0
    bodies = []


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args, **kw):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            _State.bodies.append(json.loads(raw.decode("utf-8", "replace")))
        except Exception:
            _State.bodies.append({"raw": raw[:100]})
        if _State.delay:
            time.sleep(_State.delay)
        if _State.mode == "success":
            payload = {"ok": True, "data": {"choices": [{"message": {"content": "ok"}}]}}
            code = 200
        else:
            payload = {"ok": False, "error": "model failed"}
            code = 200
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def fake_chat():
    _State.mode = "success"
    _State.delay = 0.0
    _State.bodies = []
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield srv.server_address[1]
    finally:
        srv.shutdown()
        srv.server_close()


def _run_worker(port, task="hi", timeout=5.0):
    return subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-B",
            str(WORKER),
            "--port",
            str(port),
            "--user",
            "u",
            "--session",
            "s",
            "--model",
            "",
            "--task",
            task,
            "--timeout",
            str(timeout),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
    )


def _record(timeout=5.0, task="hi"):
    return {"user_id": "u", "session_id": "s", "model": "", "task": task, "timeout": timeout}


def _wait(predicate, timeout=6.0, interval=0.02):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(interval)
    return False


# ---------- worker CLI ----------


def test_worker_success(fake_chat):
    p = _run_worker(fake_chat)
    assert p.returncode == 0, (p.stdout, p.stderr)
    d = json.loads(p.stdout.strip().splitlines()[-1])
    assert d["status"] == "done" and d["error"] == ""
    assert d["output"]["data"]["choices"][0]["message"]["content"] == "ok"


def test_worker_failure(fake_chat):
    _State.mode = "failure"
    p = _run_worker(fake_chat)
    assert p.returncode == 1, (p.stdout, p.stderr)
    d = json.loads(p.stdout.strip().splitlines()[-1])
    assert d["status"] == "failed" and "model failed" in d["error"]


# ---------- runner ----------


def test_runner_done(fake_chat, monkeypatch):
    monkeypatch.setenv("PA_GATEWAY_PORT", str(fake_chat))
    got = API._chat_entry_runner(_record())
    assert got["status"] == "done" and got["error"] == ""
    assert got["output"]["data"]["choices"][0]["message"]["content"] == "ok"


def test_runner_failed(fake_chat, monkeypatch):
    _State.mode = "failure"
    monkeypatch.setenv("PA_GATEWAY_PORT", str(fake_chat))
    got = API._chat_entry_runner(_record())
    assert got["status"] == "failed" and "model failed" in got["error"]


def test_runner_timeout(fake_chat, monkeypatch):
    _State.delay = 2.0
    monkeypatch.setenv("PA_GATEWAY_PORT", str(fake_chat))
    t0 = time.time()
    got = API._chat_entry_runner(_record(timeout=0.3))
    assert got["status"] == "failed", got
    assert "timeout" in (got.get("error") or "").lower(), got
    assert time.time() - t0 < 1.8


# ---------- API：202→done / cancel→cancelled ----------


def _api(tmp_path, monkeypatch, fake_port):
    monkeypatch.setenv("PA_GATEWAY_PORT", str(fake_port))
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


def test_runs_202_to_done(tmp_path, monkeypatch, fake_chat):
    client, svc = _api(tmp_path, monkeypatch, fake_chat)
    try:
        r = client.post("/v9/agent/runs", json={"user_id": "u", "session_id": "s", "task": "hi", "timeout": 5})
        assert r.status_code == 202, r.get_data(as_text=True)
        rid = r.get_json()["run_id"]
        assert _wait(lambda: (client.get("/v9/agent/runs/" + rid).get_json() or {}).get("state") == "done")
        d = client.get("/v9/agent/runs/" + rid).get_json()
        assert d["state"] == "done" and d["ok"] is True
    finally:
        svc.stop(cancel_queued=False)
        API.reset_run_service()


def test_runs_cancel_to_cancelled(tmp_path, monkeypatch, fake_chat):
    _State.delay = 1.0
    client, svc = _api(tmp_path, monkeypatch, fake_chat)
    try:
        r = client.post("/v9/agent/runs", json={"user_id": "u", "session_id": "s", "task": "hi", "timeout": 5})
        assert r.status_code == 202
        rid = r.get_json()["run_id"]
        assert _wait(lambda: (client.get("/v9/agent/runs/" + rid).get_json() or {}).get("state") == "running")
        c = client.post("/v9/agent/runs/" + rid + "/cancel", json={"reason": "stop"})
        assert c.status_code == 200 and c.get_json()["cancel_requested"] is True
        assert _wait(
            lambda: (client.get("/v9/agent/runs/" + rid).get_json() or {}).get("state") == "cancelled", timeout=6
        )
        assert client.get("/v9/agent/runs/" + rid).get_json()["state"] == "cancelled"
    finally:
        svc.stop(cancel_queued=False)
        API.reset_run_service()
