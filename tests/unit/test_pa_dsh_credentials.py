# -*- coding: utf-8 -*-
import os
from flask import Flask

from core.pa import dsh_credentials as DC
from core.pa.harness.dsh import DshHarness


def _reset(monkeypatch, tmp_path):
    monkeypatch.setenv("PA_DSH_ENV_FILE", str(tmp_path / "dsh.env"))
    monkeypatch.delenv(DC.ENV_NAME, raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)


def test_dsh_key_set_get_clear(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path)
    ok, face = DC.set_key("sk-test-123")
    assert ok is True
    assert DC.state()["configured"] is True
    assert DC.get_key() == "sk-test-123"
    DC.clear_key()
    assert DC.get_key() == ""


def test_dsh_key_rejects_invalid(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path)
    ok, why = DC.set_key("sk-中文，")
    assert ok is False
    assert "ASCII" in why


def test_dsh_child_env_strips_pa_key(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "pa-secret")
    env = DshHarness()._build_env()
    assert "DEEPSEEK_API_KEY" not in env


def test_dsh_child_env_maps_dsh_key(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path)
    assert DC.set_key("sk-dsh-only")[0] is True
    monkeypatch.setenv("DEEPSEEK_API_KEY", "pa-secret")
    env = DshHarness()._build_env()
    assert env["DEEPSEEK_API_KEY"] == "sk-dsh-only"


def test_harness_key_route(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path)
    from core.pa.gateway_routes import register_pa_routes
    app = Flask(__name__)
    register_pa_routes(app)
    c = app.test_client()
    r = c.get("/v9/pa/harness/key")
    assert r.status_code == 200
    assert r.get_json()["configured"] is False
    r = c.post("/v9/pa/harness/key", json={"key": "sk-route"})
    assert r.status_code == 200, r.data
    assert r.get_json()["configured"] is True
    assert c.get("/v9/pa/harness/key").get_json()["configured"] is True

def test_harness_key_route(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path)
    from core.pa.gateway_routes import register_pa_routes
    from flask import Flask
    app = Flask(__name__)
    register_pa_routes(app)
    c = app.test_client()
    assert c.get("/v9/pa/harness/key").get_json()["configured"] is False
    r = c.post("/v9/pa/harness/key", json={"key": "sk-route"})
    assert r.status_code == 200, r.data
    assert r.get_json()["configured"] is True
    assert c.get("/v9/pa/harness/key").get_json()["configured"] is True
    assert c.post("/v9/pa/harness/key", json={"key": "sk-中文"}).status_code == 400
