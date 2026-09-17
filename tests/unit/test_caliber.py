# -*- coding: utf-8 -*-
"""口径卡测试（2026-09-10，t1）"""
import sys

sys.path.insert(0, ".")
import pytest
from flask import Flask

from core.pa import caliber as C


def test_confirmed_requires_official_source():
    """confirmed 必须有官方依据(来源写进 note), 不装确认"""
    c = C.counts()
    assert c["confirmed"] >= 1, "已检索到官方文件, #1 应 confirmed"
    for card in C.CALIBER:
        if card["status"] == "confirmed":
            assert len(card["note"]) > 15, card["id"] + " confirmed 但 note 无来源说明"
    assert c["pending"] == 1


def test_all_cards_have_required_fields():
    for c in C.CALIBER:
        assert c["id"] and c["topic"] and c["status"] in ("confirmed", "unverified", "pending")
        assert "note" in c


def test_check_catches_unverified_number():
    pages = [{"data": {"title": "机会", "body": "OPC 专属贷 300 万"}}]
    hits = C.check(pages)
    assert any(h[1] == "#4" for h in hits)


def test_check_catches_multiple():
    pages = [{"data": {"title": "x", "body": "OPC 专属贷 300 万，区级政策"}}]
    ids = {h[1] for h in C.check(pages)}
    assert "#4" in ids and "#1b" in ids


def test_check_ignores_clean_content():
    pages = [{"data": {"title": "路径", "body": "选一个场景立项，跑出首版效果数据"}}]
    assert C.check(pages) == []


def test_confirmed_not_flagged():
    orig = C.CALIBER
    C.CALIBER = [dict(c, status="confirmed") for c in C.CALIBER]
    try:
        assert C.check([{"data": {"body": "1300 亿基金群可跟投"}}]) == []
    finally:
        C.CALIBER = orig


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    app = Flask(__name__)
    from core.pa.gateway_routes import register_pa_routes

    register_pa_routes(app)
    return app.test_client()


def test_route_summary(client):
    d = client.get("/v9/pa/caliber").get_json()
    assert d["ok"] and d["counts"]["confirmed"] >= 5 and len(d["cards"]) >= 10


def test_route_check(client):
    d = client.post("/v9/pa/caliber/check", json={"pages": [{"data": {"body": "OPC 专属贷 300 万"}}]}).get_json()
    assert d["ok"] and d["hit_count"] >= 1
