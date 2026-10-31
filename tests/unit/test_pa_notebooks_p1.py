# -*- coding: utf-8 -*-
"""P1 笔记本层：归属／来源／限定问答／Studio 回落／删除不删笔记。"""
import pytest
from flask import Flask

from core.pa import notebooks as NB
from core.pa import notes as N


def test_notebook_crud_and_source_counts(tmp_path):
    nb = NB.create("客户项目", "📁", "本周客户资料", data_dir=str(tmp_path))
    assert NB.list_notebooks(data_dir=str(tmp_path))[0]["id"] == nb["id"]
    n1 = NB.add_text(nb["id"], "会议纪要", "客户说下周三看方案。", ["客户"], data_dir=str(tmp_path))
    assert n1["notebook_id"] == nb["id"]
    assert NB.get(nb["id"], data_dir=str(tmp_path))["source_count"] == 1
    assert NB.sources(nb["id"], data_dir=str(tmp_path))[0]["id"] == n1["id"]
    NB.update(nb["id"], title="客户项目 A", data_dir=str(tmp_path))
    assert NB.get(nb["id"], data_dir=str(tmp_path))["title"] == "客户项目 A"


def test_delete_notebook_moves_notes_not_deletes(tmp_path):
    nb = NB.create("临时", data_dir=str(tmp_path))
    n = NB.add_text(nb["id"], "一条", "正文", data_dir=str(tmp_path))
    out = NB.delete(nb["id"], data_dir=str(tmp_path))
    assert out["moved_sources"] == 1
    assert N.get(n["id"], data_dir=str(tmp_path))["notebook_id"] == ""
    with pytest.raises(NB.NotebookError):
        NB.get(nb["id"], data_dir=str(tmp_path))


def test_ask_is_scoped_to_notebook(tmp_path):
    a = NB.create("客户", data_dir=str(tmp_path))
    b = NB.create("生活", data_dir=str(tmp_path))
    na = NB.add_text(a["id"], "会议纪要", "客户下周三看方案，需要准备报价。", data_dir=str(tmp_path))
    NB.add_text(b["id"], "购物清单", "牛奶、鸡蛋。", data_dir=str(tmp_path))
    out = NB.ask(a["id"], "客户什么时候看方案", data_dir=str(tmp_path),
                 llm_fn=lambda p: "下周三 [note:%s]" % na["id"])
    ids = [c["id"] for c in out["citations"]]
    assert ids == [na["id"]], ids


def test_ask_note_ids_only_selected_sources(tmp_path):
    nb = NB.create("选源", data_dir=str(tmp_path))
    a = NB.add_text(nb["id"], "对外", "客户预算 12 万。", data_dir=str(tmp_path))
    NB.add_text(nb["id"], "内部", "内部上限 20 万。", data_dir=str(tmp_path))
    out = NB.ask(nb["id"], "预算多少", data_dir=str(tmp_path),
                 note_ids=[a["id"]], llm_fn=lambda p: "12 万 [note:%s]" % a["id"])
    assert [c["id"] for c in out["citations"]] == [a["id"]]
    with pytest.raises(NB.NotebookError):
        NB.ask(nb["id"], "预算", data_dir=str(tmp_path), note_ids=["20261031-000000-000000"])


def test_studio_note_ids_and_recent_outputs(tmp_path):
    nb = NB.create("产出", data_dir=str(tmp_path))
    a = NB.add_text(nb["id"], "一", "事实一。", data_dir=str(tmp_path))
    NB.add_text(nb["id"], "二", "事实二。", data_dir=str(tmp_path))
    out = NB.studio(nb["id"], "summary", data_dir=str(tmp_path), note_ids=[a["id"]],
                    llm_fn=lambda p: "摘要 [note:%s]" % a["id"])
    assert out["model_ok"] is True
    saved = NB.save_output(nb["id"], "摘要笔记", out["markdown"], kind="summary", data_dir=str(tmp_path))
    rows = NB.recent_outputs(nb["id"], data_dir=str(tmp_path))
    assert rows and rows[0]["id"] == saved["id"]
    assert rows[0]["kind"] == "摘要"


def test_studio_model_ok_and_fallback(tmp_path):
    nb = NB.create("学习", data_dir=str(tmp_path))
    NB.add_text(nb["id"], "第一章", "核心概念是检索增强。", data_dir=str(tmp_path))
    ok = NB.studio(nb["id"], "summary", data_dir=str(tmp_path), llm_fn=lambda p: "## 摘要\n- 要点 [note:x]")
    assert ok["model_ok"] is True and ok["markdown"].startswith("## 摘要")
    bad = NB.studio(nb["id"], "summary", data_dir=str(tmp_path),
                    llm_fn=lambda p: (_ for _ in ()).throw(RuntimeError("down")))
    assert bad["model_ok"] is False
    assert "模型暂不可用" in bad["markdown"]
    assert bad["why"] == "RuntimeError"


def test_url_private_is_rejected(tmp_path):
    nb = NB.create("网页", data_dir=str(tmp_path))
    for u in ("http://127.0.0.1:5102/health", "http://localhost/x", "file:///etc/passwd"):
        with pytest.raises(NB.NotebookError):
            NB.add_url(nb["id"], u, data_dir=str(tmp_path))


def test_api_notebook_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "data"))
    from core.pa.gateway_routes import register_pa_routes
    app = Flask(__name__)
    register_pa_routes(app)
    c = app.test_client()
    nb = c.post("/v9/pa/notebooks", json={"title": "API 本", "emoji": "📗"}).get_json()["notebook"]
    loose = c.post("/v9/pa/notes", json={"title": "旧笔记", "body": "待迁移"}).get_json()["note"]
    moved = c.patch("/v9/pa/notes/" + loose["id"], json={"notebook_id": nb["id"]})
    assert moved.status_code == 200 and moved.get_json()["note"]["notebook_id"] == nb["id"]
    assert c.get("/v9/pa/notebooks").get_json()["notebooks"][0]["id"] == nb["id"]
    src = c.post("/v9/pa/notebooks/%s/sources/text" % nb["id"],
                 json={"title": "来源一", "body": "客户下周三看方案"}).get_json()["source"]
    ids = [x["id"] for x in c.get("/v9/pa/notebooks/%s/sources" % nb["id"]).get_json()["sources"]]
    assert src["id"] in ids and loose["id"] in ids
    monkeypatch.setattr(N, "ask", lambda q, **kw: {
        "answer": "下周三 [note:%s]" % src["id"],
        "citations": [{"id": src["id"], "title": "来源一", "snippet": "下周三"}],
        "notes": [{"id": src["id"], "title": "来源一"}]})
    r = c.post("/v9/pa/notebooks/%s/ask" % nb["id"], json={"q": "何时"})
    assert r.status_code == 200 and r.get_json()["citations"][0]["id"] == src["id"]
    monkeypatch.setattr(NB, "studio", lambda nb_id, kind="summary", **kw: {
        "kind": kind, "title": "t", "markdown": "## 摘要", "model_ok": True,
        "citations": [], "notebook_id": nb_id})
    st = c.post("/v9/pa/notebooks/%s/studio" % nb["id"], json={"kind": "summary"}).get_json()
    assert st["markdown"] == "## 摘要"
    assert c.delete("/v9/pa/notebooks/%s" % nb["id"]).status_code == 200
    assert c.get("/v9/pa/notebooks/%s" % nb["id"]).status_code == 404
