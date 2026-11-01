# -*- coding: utf-8 -*-
from types import SimpleNamespace
from core.pa import runtime_status as R


def test_runtime_view_reports_three_engines(monkeypatch):
    def fake_http(url, timeout=1.8):
        if url.endswith("/api/tags"):
            return {"ok": True, "status": 200, "error": "",
                    "data": {"models": [{"name": "qwen2.5:7b"}]}}
        if url.endswith("/api/ps"):
            return {"ok": True, "status": 200, "error": "", "data": {"models": []}}
        if url.endswith("/health"):
            return {"ok": True, "status": 200, "error": "",
                    "data": {"status": "ok", "model": "qwen2.5-7b", "loaded": True}}
        if url.endswith("/v1/models"):
            return {"ok": True, "status": 200, "error": "",
                    "data": {"data": [{"id": "qwen2.5-7b"}]}}
        return {"ok": False, "status": 0, "data": None, "error": "unexpected " + url}

    monkeypatch.setattr(R, "_http_json", fake_http)

    class FakeProbe:
        available = True
        version = "0.1.5-rc.1"
        detail = "dsh --version ⇒ 0.1.5-rc.1"

    monkeypatch.setattr("core.pa.harness.dsh.DshHarness.probe", lambda self: FakeProbe())
    out = R.runtime_view()
    assert out["ok"] is True
    by = {i["id"]: i for i in out["items"]}
    assert by["local:ollama"]["available"] is True
    assert by["local:localm"]["available"] is True
    assert by["local:localm"]["loaded_bool"] is True
    assert by["harness:dsh"]["available"] is True


def test_runtime_view_failure_is_explicit(monkeypatch):
    monkeypatch.setattr(R, "_http_json", lambda url, timeout=1.8: {
        "ok": False, "status": 0, "data": None, "error": "refused"})
    monkeypatch.setattr("core.pa.harness.dsh.DshHarness.probe",
                        lambda self: (_ for _ in ()).throw(RuntimeError("no dsh")))
    out = R.runtime_view()
    by = {i["id"]: i for i in out["items"]}
    assert by["local:ollama"]["state"] == "未接"
    assert by["local:localm"]["state"] == "未接"
    assert by["harness:dsh"]["available"] is False
    assert "no dsh" in by["harness:dsh"]["detail"]

def test_runtime_status_route(monkeypatch):
    from flask import Flask
    from core.pa.gateway_routes import register_pa_routes
    monkeypatch.setattr(R, "runtime_view", lambda: {
        "ok": True, "items": [{"id": "local:localm", "state": "在"}], "source": "test"})
    app = Flask(__name__)
    register_pa_routes(app)
    c = app.test_client()
    r = c.get("/v9/pa/runtime/status")
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["items"][0]["id"] == "local:localm"

def test_runtime_view_warns_duplicate_loaded(monkeypatch):
    def fake_http(url, timeout=1.8):
        if url.endswith("/api/tags"):
            return {"ok": True, "status": 200, "error": "", "data": {"models": [{"name": "qwen"}]}}
        if url.endswith("/api/ps"):
            return {"ok": True, "status": 200, "error": "", "data": {"models": [{"name": "qwen"}]}}
        if url.endswith("/health"):
            return {"ok": True, "status": 200, "error": "", "data": {"model": "qwen", "loaded": True}}
        if url.endswith("/v1/models"):
            return {"ok": True, "status": 200, "error": "", "data": {"data": [{"id": "qwen"}]}}
        return {"ok": False, "status": 0, "data": None, "error": "x"}
    monkeypatch.setattr(R, "_http_json", fake_http)
    monkeypatch.setattr("core.pa.harness.dsh.DshHarness.probe",
                        lambda self: (_ for _ in ()).throw(RuntimeError("no dsh")))
    out = R.runtime_view()
    assert any("同一模型同时载入" in w for w in out["warnings"])

def test_runtime_view_normalizes_colon_vs_hyphen(monkeypatch):
    def fake_http(url, timeout=1.8):
        if url.endswith("/api/tags"):
            return {"ok": True, "status": 200, "error": "", "data": {"models": [{"name": "qwen2.5:7b-instruct-q4_0-gpu"}]}}
        if url.endswith("/api/ps"):
            return {"ok": True, "status": 200, "error": "", "data": {"models": [{"name": "qwen2.5:7b-instruct-q4_0-gpu"}]}}
        if url.endswith("/health"):
            return {"ok": True, "status": 200, "error": "",
                    "data": {"model": "qwen2.5-7b-instruct-q4_0-gpu", "loaded": True}}
        if url.endswith("/v1/models"):
            return {"ok": True, "status": 200, "error": "",
                    "data": {"data": [{"id": "qwen2.5-7b-instruct-q4_0-gpu"}]}}
        return {"ok": False, "status": 0, "data": None, "error": "x"}
    monkeypatch.setattr(R, "_http_json", fake_http)
    monkeypatch.setattr("core.pa.harness.dsh.DshHarness.probe",
                        lambda self: (_ for _ in ()).throw(RuntimeError("no dsh")))
    out = R.runtime_view()
    assert any("同一模型同时载入" in w for w in out["warnings"])
