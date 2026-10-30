# -*- coding: utf-8 -*-
from core.pa import notes as N
from flask import Flask


def test_ask_with_citations(tmp_path):
    a = N.create("会议纪要", "客户说下周三看方案，需要准备报价。", ["客户"], data_dir=str(tmp_path))
    N.create("购物清单", "牛奶、鸡蛋。", ["生活"], data_dir=str(tmp_path))
    out = N.ask("客户什么时候看方案", data_dir=str(tmp_path), llm_fn=lambda p: "下周三看方案 [note:%s]" % a["id"])
    assert out["citations"]
    assert out["citations"][0]["id"] == a["id"]
    assert "下周三" in out["answer"]


def test_ask_no_match(tmp_path):
    out = N.ask("不存在的问题", data_dir=str(tmp_path), llm_fn=lambda p: "x")
    assert out["citations"] == []
    assert "没有找到" in out["answer"]


def test_ask_api(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "data"))
    from core.pa.gateway_routes import register_pa_routes
    app = Flask(__name__)
    register_pa_routes(app)
    c = app.test_client()
    a = c.post("/v9/pa/notes", json={"title": "客户方案", "body": "下周三看方案"}).get_json()["note"]
    monkeypatch.setattr(N, "ask", lambda q, limit=6: {"answer": "下周三 [note:%s]" % a["id"],
                                                     "citations": [{"id": a["id"], "title": "客户方案", "snippet": "下周三"}],
                                                     "notes": [{"id": a["id"], "title": "客户方案"}]})
    r = c.post("/v9/pa/notes/ask", json={"q": "客户什么时候看方案"})
    assert r.status_code == 200, r.data
    assert r.get_json()["citations"][0]["id"] == a["id"]
