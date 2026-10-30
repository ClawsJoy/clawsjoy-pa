"""T128：GET /v9/pa/verify/legacy_7_2 只读路由之测.

判据：
  · 环回 ⇒ 200，{ok,version,face='legacy_7_2',pass:7,fail:0,na:2,results[]}；
  · 非环回 ⇒ 403 owner_required（⛔ token · ⛔ 调 run）；唯 GET（POST 405）；
  · 旧 /v9/pa/verify 仍 404；⛔ 9/9 ／ ⛔ 14/14（face 漂移 ⇒ 200 但 ok=false）。
"""

import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lib.version import __version__  # noqa: E402
from core.pa import legacy_verify_face as LV  # noqa: E402
from core.pa.gateway_routes import register_pa_routes  # noqa: E402

URL = "/v9/pa/verify/legacy_7_2"
OLD = "/v9/pa/verify"


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    a = Flask(__name__)
    register_pa_routes(a)
    return a


def _get(app, remote="127.0.0.1", headers=None):
    return app.test_client().get(URL, environ_overrides={"REMOTE_ADDR": remote}, headers=headers or {})


def _doc(face="legacy_7_2", npass=7, nfail=0, nna=2):
    return {
        "face": face,
        "pass": npass,
        "fail": nfail,
        "na": nna,
        "results": [{"id": "C1", "status": "PASS", "evidence": {}}, {"id": "C12", "status": "N/A", "evidence": {}}],
    }


def test_loopback_200_face_7_2(app, monkeypatch):
    monkeypatch.setattr(LV, "run_legacy_7_2", lambda: _doc())
    r = _get(app)
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert set(d) == {"ok", "version", "face", "pass", "fail", "na", "results"}
    assert d["ok"] is True
    assert d["face"] == "legacy_7_2"
    assert (d["pass"], d["fail"], d["na"]) == (7, 0, 2)
    assert d["version"] == __version__
    assert d["results"] == _doc()["results"]
    assert d["pass"] != 9, "⛔ 9/9"


# 集成测：需真实 vault/活端 5102；CI 门禁以 -m "not integration" 排除（本地默认仍跑）。
@pytest.mark.integration
def test_real_route_face_7_2(app):
    """真跑（不注入）：face 7/0/2、C2/C10 PASS、C12/C13 N/A、9 条。"""
    r = _get(app)
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is True and d["face"] == "legacy_7_2"
    assert (d["pass"], d["fail"], d["na"]) == (7, 0, 2), d
    st = {x["id"]: x["status"] for x in d["results"]}
    assert st["C2"] == "PASS" and st["C10"] == "PASS"
    assert st["C12"] == "N/A" and st["C13"] == "N/A"
    assert len(d["results"]) == 9


def test_loopback_no_token_200(app, monkeypatch):
    monkeypatch.setattr(LV, "run_legacy_7_2", lambda: _doc())
    r = _get(app, headers={})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True
    assert "token" not in r.get_json()


def test_non_loopback_403_owner_required(app, monkeypatch):
    calls = []
    monkeypatch.setattr(LV, "run_legacy_7_2", lambda: calls.append(1) or _doc())
    r = _get(app, remote="192.168.3.9")
    assert r.status_code == 403, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is False and d["error"] == "owner_required", d
    assert calls == [], "非环回 ⛔ 调 run"


def test_non_loopback_with_token_still_403(app):
    r = _get(app, remote="10.0.0.8", headers={"Authorization": "Bearer x"})
    assert r.status_code == 403
    assert r.get_json()["error"] == "owner_required"


def test_post_405(app, monkeypatch):
    calls = []
    monkeypatch.setattr(LV, "run_legacy_7_2", lambda: calls.append(1) or _doc())
    r = app.test_client().post(URL, environ_overrides={"REMOTE_ADDR": "127.0.0.1"}, json={})
    assert r.status_code == 405, r.get_data(as_text=True)
    assert calls == [], "POST 405 ⇒ ⛔ 调 run"


def test_old_verify_path_still_404(app):
    r = app.test_client().get(OLD, environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 404, r.get_data(as_text=True)
    rules = [str(r.rule) for r in app.url_map.iter_rules()]
    assert OLD not in rules, "⛔ 占旧 /v9/pa/verify"


@pytest.mark.parametrize(
    "face,npass,nfail,nna",
    [
        ("legacy_9_9", 9, 0, 0),
        ("legacy_14_14", 14, 0, 0),
    ],
)
def test_drift_face_ok_false(app, monkeypatch, face, npass, nfail, nna):
    """⛔ 9/9 ／ ⛔ 14/14：face 漂移 ⇒ HTTP 200 但 ok=false（⛔ 冒成功）。"""
    monkeypatch.setattr(LV, "run_legacy_7_2", lambda: _doc(face=face, npass=npass, nfail=nfail, nna=nna))
    r = _get(app)
    assert r.status_code == 200
    d = r.get_json()
    assert d["ok"] is False
    assert d["face"] == face and d["pass"] == npass


def test_route_get_only(app):
    rules = [r for r in app.url_map.iter_rules() if str(r.rule) == URL]
    assert len(rules) == 1, rules
    methods = {m for m in rules[0].methods if m not in ("HEAD", "OPTIONS")}
    assert methods == {"GET"}, methods
