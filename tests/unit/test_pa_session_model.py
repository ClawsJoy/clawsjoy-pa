# -*- coding: utf-8 -*-
u"""P2 \u2460\uff08pm_1449 \u00a7\u4e8c.1\uff09\u4e4b\u6d4b\uff1a\u4f1a\u8bdd\u7ea7\u6a21\u578b\u4e4b\u4ed3 \uff0b \u540e\u7aef\u767d\u540d\u5355\u9a8c\u3002

\u4ee5\u4f55\u5f62\u8c03\u7528\uff08\u5224\u901a\uff0f\u65ad\u987b\u9644\uff09\uff1a
  python -X utf8 -B -m pytest tests/unit/test_pa_session_model.py -q

\u5224\u636e\uff1a
  \u24dc \u4ed3 \uff1d \u4f1a\u8bdd\u6863\u4e4b\u5b57\u6bb5\uff1aPOST \u843d\u6863 \u21d2 \u540c\u7528\u6237\u4e4b GET \u8bfb\u5f97\u540c\u503c\uff08\u26d4 \u8fdb\u7a0b\u5185\u5f02\u6b65\uff09
  \u24dd \u5f52\u4e00\uff1a`remote:deepseek-v4-flash` \u21d2 \u843d\u6863\u4e3a\u5b9e\u540d `deepseek-flash`
  \u24de **\u53cd\u63a7** \uff1a\u672a\u8bc6\u4e4b\u540d \u21d2 400 \u663e\u56e0\uff08\u26d4 \u9759\u9ed8\u56de\u843d \u00b7 \u26d4 \u4ee5\u53c2\u6570\u5145\u7ed3\u679c\uff09
  \u24df \u4e0b\u6e38\uff1a\u5bf9\u8bdd\u8f6e\u53d6\u4f1a\u8bdd\u6863\u4e4b\u6a21\u578b \u21d2 \u4f20\u81f3 `llm_brain(model=\u2026)`\uff08\u672c\u8f6e\u6240\u8bf7 \u26d4 \u76d6\u65e7\uff09
  \u24e0 \u6e05\uff1aPOST `model` \u7a7a \u21d2 \u6e05 \u21d2 \u56de\u843d\u9ed8\u8ba4
"""
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import gateway_routes as GR  # noqa: E402


def _brain_factory(captured):
    def _fake_llm_brain(system_prompt=None, model=None, max_tokens=None):
        captured["model"] = model

        def _b(context_text):
            return "\u5df2\u6536\u5230"
        _b._is_pa_brain = True
        return _b
    return _fake_llm_brain


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    captured = {}
    monkeypatch.setattr(GR, "llm_brain", _brain_factory(captured))
    app = Flask(__name__)
    GR.register_pa_routes(app, brain=GR.llm_brain())
    c = app.test_client()
    c.captured = captured
    return c


def test_session_model_store_and_normalize(client):
    u"""\u24dc \uff0b \u24dd\uff1a\u843d\u6863 \u21d2 \u8bfb\u56de\uff1b\u524d\u7f00\uff0b\u522b\u540d\u5f52\u4e00\u4e3a\u5b9e\u540d\u3002"""
    r = client.post("/v9/pa/session_model",
                    json={"user_id": "u1", "model": "remote:deepseek-v4-flash"})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert d["model"] == "deepseek-flash" and d["cleared"] is False, d
    g = client.get("/v9/pa/session_model?user_id=u1").get_json()
    assert g["model"] == "deepseek-flash" and g["model_source"] == "会话档", g
    assert "deepseek-flash" in g["known_models"], g["known_models"]
    assert g["model_aliases"].get("deepseek-v4-flash") == "deepseek-flash", g["model_aliases"]
    # \u26d4 \u540c\u7a97\uff1a\u4ed6\u7528\u6237\u4e0d\u53d7\u6c61\u67d3
    assert client.get("/v9/pa/session_model?user_id=u2").get_json()["model"] == ""


def test_session_model_rejects_unknown(client):
    u"""\u24de \u53cd\u63a7\uff1a\u672a\u8bc6\u4e4b\u540d \u21d2 400 \u663e\u56e0\uff08\u26d4 \u9759\u9ed8\u56de\u843d\uff09\u3002"""
    r = client.post("/v9/pa/session_model", json={"user_id": "u1", "model": "gpt-4"})
    assert r.status_code == 400 and not r.get_json()["ok"], r.get_json()
    assert "\u672a\u8bc6\u4e4b\u6a21\u578b\u540d" in r.get_json()["error"]
    assert client.get("/v9/pa/session_model?user_id=u1").get_json()["model"] == ""


def test_dialog_uses_session_model(client):
    u"""\u24df\uff1a\u5bf9\u8bdd\u8f6e\u53d6\u4f1a\u8bdd\u6863\u4e4b\u6a21\u578b \u21d2 \u4f20\u81f3 `llm_brain(model=\u2026)`\uff1b\u56de\u6267\u4ea6\u9644\u5b9e\u7528\u4e4b\u6a21\u578b\u3002"""
    assert client.post("/v9/pa/session_model",
                       json={"user_id": "u1", "model": "deepseek-v4-pro"}).status_code == 200
    r = client.post("/v9/pa/dialog", json={"user_id": "u1", "session_id": "s1", "text": "\u4f60\u597d"})
    assert r.status_code == 200, r.get_json()
    assert client.captured["model"] == "deepseek-v4-pro"
    assert r.get_json()["model"] == "deepseek-v4-pro"
    assert r.get_json()["model_source"] == "\u4f1a\u8bdd\u6863"


def test_dialog_turn_model_request_overrides_and_persists(client):
    u"""\u24df\u2032\uff1a\u672c\u8f6e\u6240\u8bf7\uff08\u5408\u6cd5\uff09\u21d2 \u843d\u6863 \uff0b \u672c\u8f6e\u7528\uff08\u4e00\u5904\u5b9a\u5f62\uff09\u3002"""
    r = client.post("/v9/pa/dialog", json={"user_id": "u3", "session_id": "s1",
                                          "text": "\u4f60\u597d", "model": "deepseek:deepseek-v4-flash"})
    assert r.status_code == 200, r.get_json()
    assert client.captured["model"] == "deepseek-flash"
    assert client.get("/v9/pa/session_model?user_id=u3").get_json()["model"] == "deepseek-flash"


def test_dialog_turn_model_reject_is_400(client):
    u"""\u24de\u2032\uff1a\u5bf9\u8bdd\u8f6e\u6240\u8bf7\u4e4b\u540d\u975e\u6cd5 \u21d2 400\uff08\u26d4 \u9759\u9ed8\u6e29\u548c\u56de\u843d\uff09\u3002"""
    r = client.post("/v9/pa/dialog", json={"user_id": "u1", "text": "hi", "model": "deepseek-v4.1-flash"})
    assert r.status_code == 400 and not r.get_json()["ok"], r.get_json()


def test_session_model_clear_falls_back(client):
    u"""\u24e0\uff1aPOST `model` \u7a7a \u21d2 \u6e05 \u21d2 \u56de\u843d\u9ed8\u8ba4\uff08\u26d4 \u6b8b\u7559\uff09\u3002"""
    client.post("/v9/pa/session_model", json={"user_id": "u1", "model": "deepseek-flash"})
    r = client.post("/v9/pa/session_model", json={"user_id": "u1", "model": ""})
    assert r.status_code == 200 and r.get_json()["cleared"] is True, r.get_json()
    assert client.get("/v9/pa/session_model?user_id=u1").get_json()["model"] == ""
    # \u6e05\u540e\u4e4b\u5bf9\u8bdd\u8f6e \u21d2 \u9ed8\u8ba4\u8def\uff08model=None\uff09
    client.post("/v9/pa/dialog", json={"user_id": "u1", "text": "hi"})
    assert client.captured["model"] is None