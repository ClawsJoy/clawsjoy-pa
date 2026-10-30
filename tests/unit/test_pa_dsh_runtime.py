"""task-182：DSH 外部运行时检测 API 之测（不真读 key 值）。"""

import json
import shutil
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa.gateway_routes import register_pa_routes  # noqa: E402


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    monkeypatch.delenv("PA_DSH_PATH", raising=False)
    app = Flask(__name__)
    register_pa_routes(app)
    return app.test_client()


def _body(resp):
    return resp.get_json()


def test_found_via_env_and_probe(client, monkeypatch):
    monkeypatch.setenv("PA_DSH_PATH", sys.executable)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "super-secret-key")
    r = client.get("/v9/pa/runtimes/dsh")
    assert r.status_code == 200
    d = _body(r)
    assert d["ok"] is True and d["found"] is True
    assert d["source"] == "env"
    assert d["path"] == str(Path(sys.executable).resolve())
    assert d["version"]
    assert d["cloud_supported"] is True and d["local_supported"] is False
    assert isinstance(d["install_steps"], list) and d["install_steps"]
    assert isinstance(d["node_present"], bool)
    assert d["key_present"] is True
    assert "super-secret-key" not in json.dumps(d, ensure_ascii=False)


def test_not_found_does_not_throw(client, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    r = client.get("/v9/pa/runtimes/dsh")
    assert r.status_code == 200
    d = _body(r)
    assert d["found"] is False and d["path"] is None and d["version"] is None
    assert d["source"] == "none" and d["key_present"] is False


def test_post_bad_path_400(client, tmp_path):
    r = client.post("/v9/pa/runtimes/dsh/path", json={"path": str(tmp_path / "nope")})
    assert r.status_code == 400
    assert r.get_json()["ok"] is False
    assert "not_found" in r.get_json()["error"]
    r2 = client.post("/v9/pa/runtimes/dsh/path", json={})
    assert r2.status_code == 400


def test_post_saves_atomically_and_probe_saved(client, monkeypatch, tmp_path):
    p = str(Path(sys.executable).resolve())
    r = client.post("/v9/pa/runtimes/dsh/path", json={"path": p})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["found"] is True and d["path"] == p
    saved = tmp_path / "pa" / "dsh_path.json"
    assert saved.is_file()
    assert json.loads(saved.read_text(encoding="utf-8"))["path"] == p
    monkeypatch.delenv("PA_DSH_PATH", raising=False)
    r2 = client.get("/v9/pa/runtimes/dsh")
    d2 = r2.get_json()
    assert d2["found"] is True and d2["source"] == "saved" and d2["path"] == p


def test_key_present_only_bool(client, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    d = client.get("/v9/pa/runtimes/dsh").get_json()
    assert d["key_present"] is False
    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    d2 = client.get("/v9/pa/runtimes/dsh").get_json()
    assert d2["key_present"] is True
    assert "super-secret" not in json.dumps(d2)
