# -*- coding: utf-8 -*-
u"""pm_1460 \u00a7\u4e00\uff08\u88c1\uff09\u4e4b\u6d4b\uff1a**\u56de\u6267\u5fc5\u7ed9 `kind`**\uff08\u4e00\u5904\u5b9a\u5f62\uff09\u3002

\u4ee5\u4f55\u5f62\u8c03\u7528\uff08\u5224\u901a\uff0f\u65ad\u987b\u9644\uff09\uff1a
  python -X utf8 -B -m pytest tests/unit/test_pa_receipt_kind.py -q

\u5224\u636e\uff08\u88c1\uff09\uff1a
  \u24dc `route_kind` \u4e00\u5904\u5b9a\u5f62\uff1a`ollama \u21d2 local` \uff0f `deepseek \u21d2 remote`
     \uff08\u52a0 `glm` \u21d2 remote\uff09\uff1b\u26d4 \u7a7a route \u21d2 `""`\uff1b\u672a\u8bc6 \u21d2 `"unknown"`\u3002
  \u24dd **\u9f7f**\uff08\u53cd\u63a7\uff09\uff1a\u4e34\u65f6\u5f80 `PROVIDER_KIND` \u6dfb\u4e00\u4f2a\u4f9b\u5e94\u5546 \u21d2
     `src_label` \u4e0e `route_kind` **\u540c\u6b65\u8ddf**\uff08\u8bc1\u300c\u540c\u6e90\u300d\u00b7 \u26d4 \u5404\u81ea\u590d\u8ff0\u5b57\u9762\uff09\u3002
  \u24de \u672c\u673a\u4e4b\u8f6e\uff08\u7aef\u5230\u7aef\uff09\uff1aPOST `/v9/pa/dialog` \u21d2 \u56de\u6267 `route.kind == 'local'`\u3002
  \u24df \u8fdc\u7aef\u4e4b\u8f6e\uff08\u7aef\u5230\u7aef\uff09\uff1a\u540c\u4e0a \u21d2 `route.kind == 'remote'`
     \uff08\u2b50 \u6b64\u5373\u7ea2\u7ebf\u300c\u51fa\u673a\u300d\u4e4b\u6807\u4e4b\u5f00\u5173 \u00b7 \u7f3a \u21d2 \u6807 \u26d4 \u4e0a\uff09\u3002
  \u24e0 **\u53cd\u63a7**\uff1a\u672c\u8f6e\u26d4 \u8d70\u6a21\u578b\uff08\u7a7a route\uff09\u21d2 \u56de\u6267 `route` \u26d4 \u88ab\u5851\u51fa\u5047 `kind`\u3002
"""
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import gateway_routes as GR          # noqa: E402
from core.pa import providers as PV               # noqa: E402


# ---------- \u24dc \uff0b \u24dd\uff1a\u4e00\u5904\u5b9a\u5f62 \uff0b \u9f7f ----------

def test_route_kind_single_source():
    u"""\u24dc\uff1a\u4e8c\u96c6\u4e4b\u771f\u503c \uff0b \u7a7a\uff0f\u672a\u8bc6 \u4e4b\u8fb9\u3002"""
    assert PV.route_kind({"provider": "ollama", "model": "qwen2.5:7b"}) == "local"
    assert PV.route_kind({"provider": "deepseek", "model": "deepseek-flash"}) == "remote"
    assert PV.route_kind({"provider": "glm", "model": "glm-4"}) == "remote"
    assert PV.route_kind({"provider": "anthropic", "model": "claude"}) == "remote"
    assert PV.route_kind({"provider": "who-new", "model": "x"}) == "unknown"
    assert PV.route_kind({}) == ""
    assert PV.route_kind(None) == ""
    assert PV.route_kind("ollama") == ""


def test_route_kind_shares_provider_kind_with_src_label(monkeypatch):
    u"""\u24dd \u9f7f\uff1a\u4e8c\u8005\u540c\u6e90 `PROVIDER_KIND` \u2014\u2014 \u6dfb\u4e00\u4f2a\u4f9b\u5e94\u5546 \u21d2 \u4e8c\u8005**\u540c\u6b65\u8ddf**\u3002"""
    monkeypatch.setitem(PV.PROVIDER_KIND, "fakevendor", "remote")
    assert PV.route_kind({"provider": "fakevendor"}) == "remote"
    assert PV.src_label({"provider": "fakevendor", "model": "m"}) == "src: remote:m"
    monkeypatch.setitem(PV.PROVIDER_KIND, "fakelocal", "local")
    assert PV.route_kind({"provider": "fakelocal"}) == "local"
    assert PV.src_label({"provider": "fakelocal", "model": "m"}) == "src: local:m"


# ---------- \u24de \uff0f \u24df \uff0f \u24e0\uff1a\u7aef\u5230\u7aef\u56de\u6267 ----------

def _brain_factory(route):
    def _fake_llm_brain(system_prompt=None, model=None, max_tokens=None):
        def _b(context_text):
            _b.last_route = dict(route)
            return u"\u5df2\u6536\u5230"
        _b._is_pa_brain = True
        _b.last_route = {}
        return _b
    return _fake_llm_brain


def _client(tmp_path, monkeypatch, route):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    monkeypatch.setattr(GR, "llm_brain", _brain_factory(route))
    app = Flask(__name__)
    GR.register_pa_routes(app, brain=GR.llm_brain())
    return app.test_client()


def test_dialog_receipt_kind_local(tmp_path, monkeypatch):
    u"""\u24de\uff1a\u672c\u673a\u4e4b\u8f6e \u21d2 `route.kind == 'local'`\u3002"""
    c = _client(tmp_path, monkeypatch,
                {"provider": "ollama", "model": "qwen2.5:7b", "fell_back": False, "reason": ""})
    r = c.post("/v9/pa/dialog", json={"user_id": "u1", "session_id": "s1", "text": u"\u4f60\u597d"})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert d["route"].get("kind") == "local", d.get("route")
    assert d["route"].get("provider") == "ollama", d.get("route")


def test_dialog_receipt_kind_remote(tmp_path, monkeypatch):
    u"""\u24df\uff1a\u8fdc\u7aef\u4e4b\u8f6e \u21d2 `route.kind == 'remote'`\uff08\u7ea2\u7ebf\u4e4b\u5f00\u5173\uff09\u3002"""
    c = _client(tmp_path, monkeypatch,
                {"provider": "deepseek", "model": "deepseek-flash", "fell_back": False, "reason": ""})
    r = c.post("/v9/pa/dialog", json={"user_id": "u1", "session_id": "s2", "text": u"\u4f60\u597d"})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert d["route"].get("kind") == "remote", d.get("route")
    assert d["route"].get("model") == "deepseek-flash", d.get("route")


def test_dialog_receipt_no_route_no_fake_kind(tmp_path, monkeypatch):
    u"""\u24e0 \u53cd\u63a7\uff1a\u672c\u8f6e \u26d4 \u8d70\u6a21\u578b\uff08\u7a7a route\uff09\u21d2 \u56de\u6267 \u26d4 \u88ab\u5851\u51fa\u5047 `kind`\u3002"""
    c = _client(tmp_path, monkeypatch, {})
    r = c.post("/v9/pa/dialog", json={"user_id": "u1", "session_id": "s3", "text": u"\u4f60\u597d"})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert "kind" not in (d.get("route") or {}), d.get("route")