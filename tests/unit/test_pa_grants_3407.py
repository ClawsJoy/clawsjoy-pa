# -*- coding: utf-8 -*-
u"""A2 ／ PM 3407：`GET /v9/pa/grants` 只读面 ＋ `grants._load` fail-closed。

以何形调用（判通 / 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_grants_3407.py -q

判据（PM 3407 §二 · 四条）：
  ⒈1 环回 ⇒ 200 且返 `list_grants()`
  ⒈2 非环回 ⇒ 403（承 `_loopback` 现例）
  ⒈3 `_load` 坏件 ⇒ 拒（fail-closed · ⛔ 静默回空表）
  ⒈4 件 03 之三态可分（missing ／ none ／ active ／ corrupt）＋ 字段可见
  ＋ PM 3433 §一 正形：读面 `missing` ⇒ **`200`**（`ok:true` ／ `state` ／ `count`）；
    `403` 只归**授权路径**（`is_granted(...)` ≡ False）与非环回；`corrupt` ⇒ `409`。
"""
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import grants as G  # noqa: E402
from core.pa.gateway_routes import register_pa_routes  # noqa: E402

GOOD = """version: 1
grants:
  - scene: write_file|data/reports
    decision: always
    decided_at: "2026-10-27T09:00:00"
    note: A2 正控
    uses: 0
    last_used_at: ""
  - scene: write_file|data/reports2
    decision: always
    decided_at: "2026-10-27T09:01:00"
    note: A2 正控 二
    uses: 3
    last_used_at: "2026-10-27T09:30:00"
"""


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    gf = tmp_path / "grants.yaml"
    monkeypatch.setattr(G, "grants_path", lambda: gf)
    app = Flask(__name__)
    register_pa_routes(app)
    return app, gf


def _get(app, remote="127.0.0.1"):
    return app.test_client().get("/v9/pa/grants", environ_overrides={"REMOTE_ADDR": remote})


def test_loopback_200_returns_list_grants(env):
    u"""(1) 环回 ⇒ 200 ／ `ok:true` ／ 返 `list_grants()` ＋ count ＋ source ＋ captured_at。"""
    app, gf = env
    gf.write_text(GOOD, encoding="utf-8")
    r = _get(app)
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is True and d["state"] == "active"
    assert d["grants"] == G.list_grants() and d["count"] == 2 == len(d["grants"])
    assert d["source"].endswith("grants.yaml") and d["captured_at"]
    first = d["grants"][0]
    for k in ("scene", "decision", "decided_at", "uses", "last_used_at"):
        assert k in first, k
    assert first["decision"] == "always"


def test_non_loopback_403(env):
    u"""(2) 非环回 ⇒ 403（⛔ 200）。"""
    app, gf = env
    gf.write_text(GOOD, encoding="utf-8")
    r = _get(app, remote="192.168.3.9")
    assert r.status_code == 403, r.get_data(as_text=True)
    assert r.get_json()["ok"] is False


def test_missing_read_200_state_missing(env):
    u"""(3a) 件 `missing` ⇒ **读面 `200`** ／ `ok:true` ／ `state=missing` ／ `count=0`。

    ⭐ PM `3433 §一` 正形（正 `3413 §一.1` 之混）：`403` 只归授权路径，**读面 ⛔ `403`**。
    反例：读面返 `403` ⇒ 红。
    """
    app, gf = env
    assert not gf.exists()
    r = _get(app)
    assert r.status_code == 200, r.get_data(as_text=True)   # 反例：⛔ 403
    d = r.get_json()
    assert d["ok"] is True and d["state"] == "missing"
    assert d["count"] == 0 and d["grants"] == []
    assert d["source"].endswith("grants.yaml") and d["captured_at"]


def test_missing_authz_denies(env):
    u"""(3b) 件 `missing` ⇒ **授权判** 恒 `False`（默认拒绝 —— 读面 `200` ⛔ 等于放行）。"""
    app, gf = env
    assert not gf.exists()
    assert G.is_granted("write_file|data/reports") is False
    assert G.is_granted("write_file|data/reports2") is False


def test_empty_file_is_state_none(env):
    u"""(3) 空件 ⇒ 200 ／ `state=none`（明确 0 条 —— A2-N2）。"""
    app, gf = env
    gf.write_text("", encoding="utf-8")
    d = _get(app).get_json()
    assert d["state"] == "none" and d["count"] == 0


@pytest.mark.parametrize("bad", ["grants: [\n  - scene: x\n", "grant: [unclosed", "\tgrants:: 1"])
def test_corrupt_is_rejected_409(env, bad):
    u"""(3) 坏件 ⇒ 409 ／ `ok:false` ＋ error（fail-closed · ⛔ 200 空表 —— A2-N3）。"""
    app, gf = env
    gf.write_text(bad, encoding="utf-8")
    r = _get(app)
    assert r.status_code == 409, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is False and str(d.get("error") or "").strip()
    assert "grants.yaml" in d["error"]


def test_load_fail_closed_raises(env):
    u"""(3) `_load` ／ `list_grants` 坏件 ⇒ 抛 `GrantsCorrupt`（⛔ 回空表）。"""
    app, gf = env
    gf.write_text("grants: [\n  - scene: x\n", encoding="utf-8")
    with pytest.raises(G.GrantsCorrupt):
        G._load()
    with pytest.raises(G.GrantsCorrupt):
        G.list_grants()


@pytest.mark.parametrize("bad", ["- a\n- b\n", "grants: 3\n", "grants:\n  - 7\n"])
def test_shape_errors_are_corrupt(env, bad):
    u"""(3) 形不合（非映射 ／ grants 非列表 ／ 条目非映射）⇒ 亦拒（⛔ 静默当空）。"""
    app, gf = env
    gf.write_text(bad, encoding="utf-8")
    with pytest.raises(G.GrantsCorrupt):
        G.list_grants()
    assert _get(app).status_code == 409


def test_exact_match_two_scenes_not_merged(env):
    u"""(4) 二场景各自独立可见（⛔ 合并 ／ ⛔ 前缀 —— A2-N5）。"""
    app, gf = env
    gf.write_text(GOOD, encoding="utf-8")
    scenes = [g["scene"] for g in _get(app).get_json()["grants"]]
    assert scenes == ["write_file|data/reports", "write_file|data/reports2"]
    assert G.scene_of("write_file", {"path": "data/reports2/x.md"}) != G.scene_of(
        "write_file", {"path": "data/reports/x.md"}
    )


def test_grants_path_missing_but_env_dir_untouched(env):
    u"""(4) 只读面 ⛔ 造件（⛔ 以「读」生副作用）。"""
    app, gf = env
    _get(app)
    assert not gf.exists()
