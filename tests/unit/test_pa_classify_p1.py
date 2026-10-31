# -*- coding: utf-8 -*-
"""笔记自动整理：摘要＋关键词＋归类建议。"""
import json

import pytest
from flask import Flask

from core.pa import classify as C
from core.pa import notebooks as NB
from core.pa import notes as N


def test_classify_fallback_when_model_down(tmp_path):
    n = N.create("客户会议纪要", "客户下周三看方案，预算 12 万，风险是退货。", ["客户"], data_dir=str(tmp_path))
    out = C.classify_note(n["id"], data_dir=str(tmp_path),
                          llm_fn=lambda p: (_ for _ in ()).throw(RuntimeError("down")))
    assert out["model_ok"] is False and out["why"] == "RuntimeError"
    assert out["summary"] and out["keywords"]
    saved = N.get(n["id"], data_dir=str(tmp_path))
    assert saved["summary"] == out["summary"]
    assert saved["keywords"] == out["keywords"]


def test_classify_model_json(tmp_path):
    n = N.create("项目", "这是正文", data_dir=str(tmp_path))
    fake = json.dumps({"summary": "一句摘要", "keywords": ["预算", "风险"], "topic": "项目风险"}, ensure_ascii=False)
    out = C.classify_note(n["id"], data_dir=str(tmp_path), llm_fn=lambda p: fake)
    assert out["model_ok"] is True
    assert out["keywords"] == ["预算", "风险"]
    assert out["topic"] == "项目风险"


def test_suggest_notebook_by_keywords(tmp_path):
    nb = NB.create("客户项目", "客户 预算 方案", data_dir=str(tmp_path))
    res = {"keywords": ["客户", "预算"], "summary": "客户预算", "topic": "客户"}
    s = C.suggest_notebook(res, data_dir=str(tmp_path))
    assert s["notebook_id"] == nb["id"] and s["new"] is False


def test_suggest_new_notebook_when_no_match(tmp_path):
    NB.create("生活", "购物 做饭", data_dir=str(tmp_path))
    res = {"keywords": ["量子"], "summary": "量子计算", "topic": "量子计算"}
    s = C.suggest_notebook(res, data_dir=str(tmp_path))
    assert s["new"] is True and s["title"] == "量子计算"


def test_classify_api(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "data"))
    from core.pa.gateway_routes import register_pa_routes
    app = Flask(__name__)
    register_pa_routes(app)
    c = app.test_client()
    n = c.post("/v9/pa/notes", json={"title": "客户", "body": "客户预算 12 万"}).get_json()["note"]
    monkeypatch.setattr(C, "classify_note", lambda nid, **kw: {
        "id": nid, "title": "客户", "summary": "客户预算", "keywords": ["预算"],
        "topic": "客户", "model_ok": True, "why": ""})
    r = c.post("/v9/pa/notes/%s/classify" % n["id"])
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["summary"] == "客户预算"
    assert "suggestion" in d
