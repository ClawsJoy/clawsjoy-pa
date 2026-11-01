# -*- coding: utf-8 -*-
from core.pa import providers as P
from core.pa.providers import (
    DEFAULT_PROVIDER, PROVIDERS, available_state, known_models,
    models_table, provider_kind, public_view, resolve_model,
)


def test_localm_registered_and_not_default():
    assert "local:localm" in PROVIDERS
    assert DEFAULT_PROVIDER == "local:ollama"
    assert provider_kind("local:localm") == "local"
    assert "localm:qwen2.5-7b-instruct-q4_0-gpu" in known_models()


def test_localm_model_prefix_survives_resolve():
    assert resolve_model("localm:qwen2.5-7b-instruct-q4_0-gpu") == "localm:qwen2.5-7b-instruct-q4_0-gpu"
    # 裸名仍归 Ollama，不会把 localm 偷换成默认
    assert resolve_model("qwen2.5:7b-instruct-q4_0-gpu") == "qwen2.5:7b-instruct-q4_0-gpu"


def test_localm_available_state_and_table(monkeypatch):
    monkeypatch.setattr(P, "_tcp_open", lambda *a, **k: True)
    st, why = available_state("local:localm")
    assert st == "在"
    assert "8642" in why
    view = public_view()
    rows = [r for r in view["models_table"] if r["provider_id"] == "local:localm"]
    assert rows and rows[0]["id"].startswith("localm:")
    assert rows[0]["kind"] == "local"

def test_llm_client_localm_route_no_ollama_fallback(monkeypatch):
    from core.lib.llm_client import LLMClient
    c = LLMClient()
    seen = {}

    def fake_openai(*args, **kwargs):
        seen.update(kwargs)
        if False:
            yield
        return "LOCALM_OK"

    monkeypatch.setattr(c, "_call_openai_compatible", fake_openai)
    out = c.generate("hi", model="localm:qwen2.5-7b-instruct-q4_0-gpu", max_tokens=8)
    assert out == "LOCALM_OK"
    assert seen.get("allow_no_key") is True
    assert str(seen.get("endpoint") or "").endswith("/v1")
    route = c.get_last_route()
    assert route.get("provider") == "localm"
    assert route.get("fell_back") is False

def test_localm_dynamic_models_enter_registry(monkeypatch):
    monkeypatch.setattr(P, "_discover_localm_models", lambda: [
        {"id": "localm:qwen2.5vl-7b", "label": "LocaLM · qwen2.5vl-7b",
         "isDefault": False, "ctx": 8192, "loaded": False}])
    monkeypatch.setattr(P, "_LOCALM_CACHE", {"at": 0.0, "models": None})
    view = P.public_view()
    rows = [r for r in view["models_table"] if r["provider_id"] == "local:localm"]
    assert any(r["id"] == "localm:qwen2.5vl-7b" for r in rows)
    assert P.resolve_model("localm:qwen2.5vl-7b") == "localm:qwen2.5vl-7b"
