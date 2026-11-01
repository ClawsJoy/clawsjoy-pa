# -*- coding: utf-8 -*-
from flask import Flask
from core.pa import notes as N
from core.pa.gateway_routes import register_pa_routes

MODEL = "localm:qwen2.5-7b-instruct-q4_0-gpu"


def test_ask_uses_explicit_model(tmp_path, monkeypatch):
    N.create("客户", "预算 12 万", ["客户"], data_dir=str(tmp_path))
    seen = {}

    def fake_llm(prompt, **kw):
        seen.update(kw)
        return "预算 12 万 [note:x]"

    monkeypatch.setattr(N, "llm_generate", fake_llm)
    out = N.ask("预算多少", data_dir=str(tmp_path), model=MODEL)
    assert seen.get("model") == MODEL
    assert out.get("model") == MODEL
    assert out.get("model_ok") is True


def test_notes_ask_route_passes_model(monkeypatch):
    app = Flask(__name__)
    register_pa_routes(app)
    seen = {}

    def fake_ask(q, limit=6, model=None):
        seen["model"] = model
        return {"answer": "ok", "citations": [], "model": model, "model_ok": True}

    monkeypatch.setattr(N, "ask", fake_ask)
    c = app.test_client()
    r = c.post("/v9/pa/notes/ask", json={"q": "q", "model": MODEL})
    assert r.status_code == 200, r.data
    assert seen.get("model") == MODEL
    assert r.get_json()["model"] == MODEL


def test_notes_ask_route_rejects_unknown_model(monkeypatch):
    app = Flask(__name__)
    register_pa_routes(app)
    c = app.test_client()
    r = c.post("/v9/pa/notes/ask", json={"q": "q", "model": "nope:model"})
    assert r.status_code == 400
