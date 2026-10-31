# -*- coding: utf-8 -*-
"""来源标签（label）与自动标签撤销。"""
import pytest
from flask import Flask

from core.pa import labels as L
from core.pa import notes as N


def test_label_crud_and_move(tmp_path):
    L.add("合规", data_dir=str(tmp_path))
    L.add("渠道", data_dir=str(tmp_path))
    assert [x["name"] for x in L.list_labels(str(tmp_path))] == ["合规", "渠道"]
    n = N.create("客户", "正文", data_dir=str(tmp_path))
    N.update(n["id"], category="合规", category_auto=False, data_dir=str(tmp_path))
    L.rename("合规", "合规与认证", data_dir=str(tmp_path))
    assert N.get(n["id"], data_dir=str(tmp_path))["category"] == "合规与认证"
    assert [x["name"] for x in L.list_labels(str(tmp_path))] == ["合规与认证", "渠道"]
    out = L.delete("渠道", data_dir=str(tmp_path))
    assert out["deleted"] == "渠道"


def test_clear_auto_labels_only(tmp_path):
    a = N.create("自动", "正文", data_dir=str(tmp_path))
    b = N.create("手动", "正文", data_dir=str(tmp_path))
    N.update(a["id"], category="自动标签", category_auto=True, data_dir=str(tmp_path))
    N.update(b["id"], category="手动标签", category_auto=False, data_dir=str(tmp_path))
    assert N.clear_auto_labels(str(tmp_path)) == 1
    assert N.get(a["id"], data_dir=str(tmp_path))["category"] == ""
    assert N.get(b["id"], data_dir=str(tmp_path))["category"] == "手动标签"


def test_labels_api(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "data"))
    from core.pa.gateway_routes import register_pa_routes
    app = Flask(__name__)
    register_pa_routes(app)
    c = app.test_client()
    r = c.post("/v9/pa/labels", json={"name": "测试标签"})
    assert r.status_code == 200, r.data
    assert c.get("/v9/pa/labels").get_json()["labels"][0]["name"] == "测试标签"
    n = c.post("/v9/pa/notes", json={"title": "n", "body": "b"}).get_json()["note"]
    r = c.post("/v9/pa/notes/%s/label" % n["id"], json={"category": "测试标签"})
    assert r.get_json()["note"]["category"] == "测试标签"
    r = c.post("/v9/pa/notes/unlabel_auto")
    assert r.get_json()["cleared"] == 0
