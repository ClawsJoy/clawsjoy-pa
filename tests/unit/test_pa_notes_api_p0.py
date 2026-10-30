# -*- coding: utf-8 -*-
import os
from flask import Flask


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "data"))
    from core.pa.gateway_routes import register_pa_routes
    app = Flask(__name__)
    register_pa_routes(app)
    app.config.update(TESTING=True)
    return app.test_client()


def test_notes_api_roundtrip(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.post("/v9/pa/notes", json={"title": "API笔记", "body": "内容", "tags": ["api"]})
    assert r.status_code == 200, r.data
    nid = r.get_json()["note"]["id"]
    assert c.get("/v9/pa/notes?q=API").get_json()["notes"]
    assert c.get("/v9/pa/notes/" + nid).get_json()["note"]["body"] == "内容"
    assert c.patch("/v9/pa/notes/" + nid, json={"body": "改"}).status_code == 200
    assert c.delete("/v9/pa/notes/" + nid).status_code == 200
    assert c.get("/v9/pa/notes/" + nid).status_code == 404


def test_notes_api_import_reindex(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.md").write_text("# A\n\nA body\n", encoding="utf-8")
    r = c.post("/v9/pa/notes/import", json={"path": str(src)})
    assert r.status_code == 200, r.data
    assert r.get_json()["imported"] == 1
    assert c.post("/v9/pa/notes/reindex").get_json()["indexed"] == 1
