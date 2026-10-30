# -*- coding: utf-8 -*-
u"""T121：GET /v9/pa/relations/status 只读状态面之测。

判据（task-121）：
  · 环回 ⇒ 200，返 {ok,version,ledger:{ok,total,bad,superseded,max_age_days},source}；
  · 非环回 ⇒ 403 owner_required（⛔ token 判据 · ⛔ 读账）；
  · 只读：⛔ 写账 ／ ⛔ 改账（ledger 字节不变 · 唯 verify 一次）；
  · ledger ＝ evidence_ledger.verify(默认账, max_age_days=30) 摘要；
  · POST ⇒ 405（本面唯 GET）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_pa_relations_status.py -q
"""
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lib.version import __version__  # noqa: E402
from core.pa import evidence_ledger as EL  # noqa: E402
from core.pa.gateway_routes import register_pa_routes  # noqa: E402

URL = "/v9/pa/relations/status"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    ledger = tmp_path / "evidence_ledger.jsonl"
    ledger.write_text("", encoding="utf-8")
    monkeypatch.setattr(EL, "default_ledger_path", lambda: ledger)
    calls = []

    def _fake_verify(path, max_age_days=None, **kw):
        calls.append({"path": str(path), "max_age_days": max_age_days, "kw": kw})
        return {"ok": True, "total": 2, "bad": [], "superseded": []}

    monkeypatch.setattr(EL, "verify", _fake_verify)
    app = Flask(__name__)
    register_pa_routes(app)
    return app, ledger, calls


def _get(app, remote="127.0.0.1", headers=None):
    return app.test_client().get(URL, environ_overrides={"REMOTE_ADDR": remote},
                                 headers=headers or {})


def test_loopback_200_status_shape(env):
    app, ledger, calls = env
    r = _get(app)
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is True
    assert d["ok"] is d["ledger"]["ok"], u"T126：外层 ok ≡ 账 ok"
    assert d["version"] == __version__
    assert d["source"] == str(ledger)
    assert d["ledger"] == {"ok": True, "total": 2, "bad": [], "superseded": [],
                           "max_age_days": 30}, d["ledger"]
    assert set(d["ledger"]) == {"ok", "total", "bad", "superseded", "max_age_days"}
    # 唯一次 verify · 默认账 · 30 天保鲜（⛔ 写账）
    assert calls == [{"path": str(ledger), "max_age_days": 30, "kw": {}}], calls


def test_loopback_200_without_token(env):
    u"""⛔ token 判据：无 Authorization 亦 200（本面唯环回门）。"""
    app, _ledger, _calls = env
    r = _get(app, headers={})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is True
    assert "token" not in d and "token" not in d["ledger"]


def test_non_loopback_403_owner_required(env):
    app, _ledger, calls = env
    r = _get(app, remote="192.168.3.9")
    assert r.status_code == 403, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is False and d["error"] == "owner_required", d
    assert calls == [], u"非环回 ⛔ 读账（403 前拦）"


def test_non_loopback_403_even_with_tokenish_header(env):
    u"""非环回：带 Authorization 亦 403（⛔ token 门 · 唯环回）。"""
    app, _ledger, calls = env
    r = _get(app, remote="10.0.0.8", headers={"Authorization": "Bearer x"})
    assert r.status_code == 403, r.get_data(as_text=True)
    assert r.get_json()["error"] == "owner_required"
    assert calls == []


def test_post_405(env):
    app, _ledger, calls = env
    r = app.test_client().post(URL, environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
                               json={})
    assert r.status_code == 405, r.get_data(as_text=True)
    assert calls == [], u"POST 405 ⇒ ⛔ 读账"


def test_read_only_ledger_bytes_unchanged(env):
    app, ledger, _calls = env
    before = ledger.read_bytes()
    r = _get(app)
    assert r.status_code == 200
    assert ledger.read_bytes() == before, u"本面须只读（⛔ 写账／改账）"


def test_ledger_bad_and_superseded_propagated(monkeypatch, tmp_path):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("", encoding="utf-8")
    monkeypatch.setattr(EL, "default_ledger_path", lambda: ledger)
    bad = [{"line": 3, "reason": "印不符（疑篡改）", "path": "core/pa/relations.py"}]
    superseded = [{"line": 3, "path": "core/pa/relations.py",
                   "sha16": "ad42e425f9687bb6", "reason": "superseded"}]
    monkeypatch.setattr(EL, "verify",
                        lambda path, max_age_days=None, **kw:
                        {"ok": False, "total": 5, "bad": bad, "superseded": superseded})
    app = Flask(__name__)
    register_pa_routes(app)
    r = _get(app)
    assert r.status_code == 200, r.get_data(as_text=True)   # 状态面照实报 bad，⛔ 500
    d = r.get_json()
    assert d["ok"] is False, u"T126：账坏 ⇒ 外层 ok=false（HTTP 仍 200）"
    assert d["ok"] is d["ledger"]["ok"], u"外层 ok ≡ 账 ok"
    assert d["ledger"]["ok"] is False
    assert d["ledger"]["total"] == 5
    assert d["ledger"]["bad"] == bad
    assert d["ledger"]["superseded"] == superseded
    assert d["ledger"]["max_age_days"] == 30
    assert d["version"] == __version__


@pytest.mark.parametrize("ledger_ok", [True, False])
def test_outer_ok_equals_ledger_ok(monkeypatch, tmp_path, ledger_ok):
    u"""T126：外层 ok 恒等于 ledger.ok（好账 true ／ 坏账 false），HTTP 均 200。"""
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("", encoding="utf-8")
    monkeypatch.setattr(EL, "default_ledger_path", lambda: ledger)
    monkeypatch.setattr(EL, "verify",
                        lambda path, max_age_days=None, **kw:
                        {"ok": ledger_ok, "total": 2, "bad": [], "superseded": []})
    app = Flask(__name__)
    register_pa_routes(app)
    r = _get(app)
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is ledger_ok
    assert d["ok"] is d["ledger"]["ok"]
    assert d["version"] == __version__ and d["source"] == str(ledger)


def test_route_registered_get_only(env):
    app, _ledger, _calls = env
    rules = [r for r in app.url_map.iter_rules() if str(r.rule) == URL]
    assert len(rules) == 1, rules
    methods = {m for m in rules[0].methods if m not in ("HEAD", "OPTIONS")}
    assert methods == {"GET"}, methods
