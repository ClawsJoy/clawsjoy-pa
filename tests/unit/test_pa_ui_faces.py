# -*- coding: utf-8 -*-
u"""UI 面册（`GET /v9/pa/ui_faces`）之测（承 pm_1384 §三.1 · 判成 ⒞）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_ui_faces.py -q

判据：
  ⒈ `面之数` ≡ `web/pa/faces/*.js`（剔 `*.before_*`）之数 —— ⛔ 旁源 `faces.json` 之数
  ⒉ `requires` 逐条皆在既有 `/v9/pa/*` 路由集内（`悬` 为空）
  ⒊ 响应 ⛔ 绝对径（`file` 皆 `faces/<名>.js` 之相对径 · ⛔ 本机之径入面）
  ⒋ 旁源对映漂**照实报**（⛔ 静默）＋ 结构自洽（多出 ／ 缺 ≡ 对称差）
  ⒌ 反控：假路由必判「悬」（`/v9/pa/agents` ＝ 已撤之实例）／真路由必判「在」／
     注内之路由 ⛔ 入 `requires`（⛔ 无齿之闸 ＝ 假绿）
"""
import io
import json
import os
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import gateway_routes as G  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    app = Flask(__name__)
    G.register_pa_routes(app)
    app.config["TESTING"] = True
    return app.test_client()


def _ro():
    return G._ui_faces_readout()


def _disk_ids():
    return sorted(p.name[:-3] for p in G.UI_FACES_DIR.glob("*.js")
                  if not p.name.startswith(".") and ".before_" not in p.name)


def _manifest_ids():
    with io.open(str(G.UI_FACES_MANIFEST), encoding="utf-8") as fh:
        j = json.load(fh)
    return sorted(f["id"] for f in (j.get("faces") or []) if f.get("id"))


def test_面之数_equals_disk():
    u"""⭐ 判成 ⒞（一）：面之数 ≡ 盘上之件数（⛔ 旁源之数）。"""
    ro = _ro()
    ids = _disk_ids()
    assert ro["面之数"] == len(ids), (ro["面之数"], len(ids))
    assert [f["id"] for f in ro["faces"]] == ids
    # ⭐ ⛔ 以旁源之数代真源之数 —— 二源之漂须**分报**（今 旁源 22 ／ 盘上 21 ⇒ 漂 2：selfdesc ／ sources）
    d = ro["对映"]
    assert "faces/*.js" in d["真源"] and "faces.json" in d["旁源"]
    assert d["旁源之数"] == len(_manifest_ids())


def test_requires_all_known():
    u"""⭐ 判成 ⒞（二）：逐 requires 皆在既有 /v9/pa/* 路由集内（⛔ 悬）。"""
    ro = _ro()
    assert ro["悬"] == {}, ro["悬"]
    assert sum(len(f["requires"]) for f in ro["faces"]) > 0, "requires 全空 ＝ 弱闸"


def test_no_absolute_path_in_payload():
    u"""⛔ 绝对径入面（承 pm_1384 §三「⛔ 绝对径之字面入 git」之族）。"""
    ro = _ro()
    blob = json.dumps(ro, ensure_ascii=False)
    assert str(G._UI_REPO) not in blob
    assert str(ROOT) not in blob
    for f in ro["faces"]:
        assert f["file"].startswith("faces/"), f["file"]
        assert ":" not in f["file"], f["file"]


def test_旁源对映漂_照实报_且结构自洽():
    ids, mids = set(_disk_ids()), set(_manifest_ids())
    d = _ro()["对映"]
    assert d["旁源之数"] == len(mids), (d["旁源之数"], len(mids))
    assert set(d["旁源多出（⛔ 盘上无件）"]) == mids - ids
    assert set(d["旁源缺（盘上有件）"]) == ids - mids


def test_反控_真路由判在_假路由判悬():
    rs = G._ui_route_set()
    assert G._ui_route_known("/v9/pa/roster", rs) is True
    assert G._ui_route_known("/v9/pa/agents", rs) is False, "已撤之名（more.js 注）误判「在」"
    assert G._ui_route_known("/v9/pa/no_such_thing", rs) is False
    assert G._ui_route_known("/v9/pa/roster", set()) is False, "空路由集须判「悬」（⛔ 默认放行）"


def test_反控_注内之路由不入_requires():
    u"""more.js 之注书「⛔ 自造 `/v9/pa/agents`（该名已撤）」⇒ 剔注方为真。"""
    ro = _ro()
    more = {f["id"]: f for f in ro["faces"]}["more"]
    assert "/v9/pa/agents" not in more["requires"]
    arch = {f["id"]: f for f in ro["faces"]}["archive"]
    assert all("threads_" not in r for r in arch["requires"]), arch["requires"]


def test_http_route_200_and_stamped(client):
    u"""⭐ 经蓝图（真注册）之活读：200 ＋ 印 ／ version ／ 面之数 皆在。"""
    r = client.get("/v9/pa/ui_faces")
    assert r.status_code == 200
    d = r.get_json()
    assert d["ok"] is True
    assert d["version"] == G.PA_UI_FACES_VERSION
    assert d["面之数"] == len(_disk_ids())
    assert isinstance(d.get("印"), str) and len(d["印"]) == 16, d.get("印")

