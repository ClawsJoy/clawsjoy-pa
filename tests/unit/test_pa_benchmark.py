# -*- coding: utf-8 -*-
from flask import Flask
from core.pa import benchmark as B


class FakeResp:
    status_code = 200
    def __init__(self, lines): self._lines = lines
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def iter_lines(self): return iter(self._lines)


def test_bench_ollama_parses_ttft_and_eval(monkeypatch):
    lines = [
        b'{"response":"a"}\n',
        b'{"response":"b"}\n',
        b'{"done":true,"eval_count":10,"eval_duration":500000000}\n',
    ]
    monkeypatch.setattr("requests.post", lambda *a, **k: FakeResp(lines))
    monkeypatch.setattr(B, "_vram_mib", lambda: 1000)
    d = B.bench_ollama("m", prompt="p", max_tokens=8)
    assert d["ok"] is True
    assert d["ttft_ms"] is not None
    assert d["tok_s"] == 20.0
    assert d["tokens"] == 10


def test_bench_localm_stream(monkeypatch):
    lines = [
        b'data: {"choices":[{"delta":{"content":"a"}}]}\n',
        b'data: {"choices":[{"delta":{"content":"b"}}]}\n',
        b'data: {"choices":[{"delta":{"content":"c"}}],"usage":{"completion_tokens":3}}\n',
        b'data: [DONE]\n',
    ]
    monkeypatch.setattr("requests.post", lambda *a, **k: FakeResp(lines))
    monkeypatch.setattr(B, "_vram_mib", lambda: 1000)
    d = B.bench_localm("localm:m", prompt="p", max_tokens=8)
    assert d["ok"] is True
    assert d["tokens"] == 3
    assert d["tok_s_source"] == "usage.completion_tokens"


def _app():
    from core.pa.gateway_routes import register_pa_routes
    app = Flask(__name__)
    register_pa_routes(app)
    return app


def test_benchmark_route(monkeypatch):
    app = _app()
    monkeypatch.setattr(B, "run", lambda *a, **k: {
        "ok": True, "engine": "localm", "ttft_ms": 1, "tok_s": 2, "tokens": 3})
    c = app.test_client()
    r = c.post("/v9/pa/benchmark", json={"engine": "localm"})
    assert r.status_code == 200, r.data
    assert r.get_json()["engine"] == "localm"


def test_benchmark_route_rejects_bad_engine(monkeypatch):
    app = _app()
    c = app.test_client()
    assert c.post("/v9/pa/benchmark", json={"engine": "cloud"}).status_code == 400
