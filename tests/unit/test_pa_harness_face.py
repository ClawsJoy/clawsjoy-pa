# -*- coding: utf-8 -*-
from flask import Flask
from core.pa import harness_face as HF
from core.pa.gateway_routes import register_pa_routes


def _app():
    app = Flask(__name__)
    register_pa_routes(app)
    return app


def test_harness_runs_route(monkeypatch):
    monkeypatch.setattr(HF, "list_runs", lambda limit=20: {
        "runs": [{"run_id": "r1", "status": "ok", "task": "t"}], "ledger": {}})
    c = _app().test_client()
    r = c.get("/v9/pa/harness/runs")
    assert r.status_code == 200
    assert r.get_json()["runs"][0]["run_id"] == "r1"


def test_harness_run_route(monkeypatch):
    seen = {}

    def fake_run(task, cwd="", timeout=120):
        seen["task"] = task
        seen["timeout"] = timeout
        return {"run_id": "r2", "status": "ok", "task": task, "events": []}

    monkeypatch.setattr(HF, "run_dsh", fake_run)
    c = _app().test_client()
    r = c.post("/v9/pa/harness/run", json={"task": "只回答 OK", "timeout": 10})
    assert r.status_code == 200, r.data
    assert seen["task"] == "只回答 OK"
    assert r.get_json()["run_id"] == "r2"


def test_harness_run_requires_task(monkeypatch):
    c = _app().test_client()
    assert c.post("/v9/pa/harness/run", json={"task": "  "}).status_code == 400
