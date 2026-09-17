# -*- coding: utf-8 -*-
"""PA 编队花名册测试（2026-09-10）

战略背景: 要"调度市面上所有 agent 协作", 先得结构化地知道能调度谁/怎么调/边界在哪。
核心纪律: verified/boundary/fragility 必须有实测来源, 未验证标 unverified, 不虚报能力。
"""
import os
import sys
import tempfile

sys.path.insert(0, ".")
import pytest
from flask import Flask

os.environ.setdefault("PA_DATA_DIR", tempfile.mkdtemp())


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    app = Flask(__name__)
    from core.pa.gateway_routes import register_pa_routes

    register_pa_routes(app)
    return app.test_client()


def test_seed_cards_present():
    from core.pa import roster as R

    s = R.summary()
    ids = {r["id"] for r in s["rows"]}
    for must in ("ds_chat", "lingxi", "lingxi_local_api", "blender", "local_vlm", "v9_agent"):
        assert must in ids, "缺卡片: %s" % must


def test_every_card_has_boundary_and_fragility():
    """纪律: 每张卡都必须写明【做不到什么】和【有多脆】, 只写能力的花名册会误导派活"""
    from core.pa import roster as R

    for c in R.load()["cards"]:
        assert c.get("capabilities"), c["id"]
        assert c.get("boundary"), "%s 缺 boundary" % c["id"]
        assert c.get("fragility"), "%s 缺 fragility" % c["id"]
        assert (c.get("access") or {}).get("level") in R.ACCESS_LADDER, "%s 级别非法" % c["id"]


def test_by_capability():
    from core.pa import roster as R

    assert [x["id"] for x in R.by_capability("图文识别")] == ["ds_chat"]
    assert "lingxi" in [x["id"] for x in R.by_capability("排版")]
    assert R.by_capability("不存在的能力xyz") == []


def test_upsert_add_and_partial_update():
    from core.pa import roster as R

    R.upsert({"id": "test_agent", "name": "测试", "capabilities": ["x"]})
    assert R.get("test_agent")["name"] == "测试"
    # 局部更新不得抹掉既有字段
    R.upsert({"id": "test_agent", "verified": ["v1"]})
    c = R.get("test_agent")
    assert c["name"] == "测试" and c["verified"] == ["v1"]


def test_upsert_requires_id():
    from core.pa import roster as R

    assert R.upsert({"name": "no id"})["ok"] is False


def test_routes(client):
    r = client.get("/v9/pa/roster")
    assert r.status_code == 200 and r.get_json()["count"] >= 6
    r2 = client.get("/v9/pa/roster/find?cap=图文识别")
    assert r2.get_json()["candidates"][0]["id"] == "ds_chat"
    assert client.get("/v9/pa/roster/ds_chat").get_json()["card"]["name"].startswith("@DS Chat")
    assert client.get("/v9/pa/roster/nope").status_code == 404
    r3 = client.post("/v9/pa/roster/upsert", json={"card": {"id": "z1", "name": "Z", "capabilities": ["z"]}})
    assert r3.get_json()["ok"] and client.get("/v9/pa/roster/z1").status_code == 200
