# -*- coding: utf-8 -*-
"""2026-09-10 PA 网关接线测试: /v9/pa/* (独立 Flask app, 不 import 网关单体)。"""
import sys

sys.path.insert(0, ".")
import pytest
from flask import Flask

from core.pa.gateway_routes import register_pa_routes


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    app = Flask(__name__)
    register_pa_routes(app)
    return app.test_client()


def test_context(client):
    r = client.get("/v9/pa/context")
    assert r.status_code == 200
    d = r.get_json()
    assert d["ok"] and d["counts"]["ledger"] >= 3
    assert d["counts"]["profile"] >= 1 and d["counts"]["profile"] <= 20
    assert all(e.get("status") == "confirmed" for e in d["profile"])


def test_sediment_with_emotion_domain(client):
    r = client.post(
        "/v9/pa/sediment", json={"domain": "emotion", "value": "老板在意留白与数字突出", "source": "test", "confidence": "high"}
    )
    assert r.status_code == 200 and r.get_json()["ok"]
    r2 = client.get("/v9/pa/profile?domain=emotion")
    vals = [e["value"] for e in r2.get_json()["entries"]]
    assert any("留白" in v for v in vals)


def test_sediment_requires_fields(client):
    r = client.post("/v9/pa/sediment", json={"domain": "aesthetic"})
    assert r.status_code == 400 and not r.get_json()["ok"]


def test_dialog_goal_oriented_and_interruptible(client):
    r1 = client.post("/v9/pa/dialog", json={"session_id": "s1", "text": "先定 A 主题封面", "topic": "样张A"})
    assert r1.get_json()["ok"] and r1.get_json()["topic"] == "样张A"
    r2 = client.post("/v9/pa/dialog", json={"session_id": "s1", "text": "改看数据页", "topic": "数据页"})
    assert r2.get_json()["topic"] == "数据页"
    h = client.get("/v9/pa/dialog?session_id=s1").get_json()
    topics = [m.get("topic") for m in h["history"] if m.get("role") == "user"]
    assert "样张A" in topics and "数据页" in topics


def test_ledger_add_and_done(client):
    r = client.post("/v9/pa/ledger/add", json={"title": "测试待办", "kind": "todo"})
    tid = r.get_json()["item"]["id"]
    assert client.post("/v9/pa/ledger/done", json={"id": tid}).get_json()["ok"]
    items = client.get("/v9/pa/ledger").get_json()
    assert all(i["id"] != tid for i in items["open"])


def test_dispatch_stub_pass(client):
    r = client.post("/v9/pa/dispatch", json={"task_text": "生成一份测试交付物"})
    d = r.get_json()
    assert d["ok"] and d["review"]["verdict"] == "pass"
    h = client.get("/v9/pa/dispatch/history").get_json()
    assert any(row["task_id"] == d["contract"]["task_id"] for row in h["rows"])


def test_dialog_uses_injected_brain(tmp_path, monkeypatch):
    """注入 brain: dialog 回复来自 brain(LLM), 不再是模板。"""
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    from flask import Flask

    from core.pa.gateway_routes import register_pa_routes

    app = Flask(__name__)
    register_pa_routes(app, brain=lambda ctx: "【PA 脑】已理解，建议先圈 A 主题（默认），备选 B。")
    cl = app.test_client()
    d = cl.post("/v9/pa/dialog", json={"session_id": "s9", "text": "样张怎么定?", "topic": "样张"}).get_json()
    assert d["ok"] and d["reply"].startswith("【PA 脑】")


def test_dialog_falls_back_when_brain_fails(tmp_path, monkeypatch):
    """brain 抛异常 -> 降级模板回复, 不 500。"""
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    from flask import Flask

    from core.pa.gateway_routes import register_pa_routes

    def boom(ctx):
        raise RuntimeError("llm down")

    app = Flask(__name__)
    register_pa_routes(app, brain=boom)
    cl = app.test_client()
    r = cl.post("/v9/pa/dialog", json={"session_id": "s10", "text": "在吗"})
    assert r.status_code == 200 and r.get_json()["ok"]


# ===== 2026-09-13 参数化收集入口接线（表单 + 聊天 同一条落库路径）=====
FIELD_KEYS = {
    "industry",
    "interests",
    "report_detail",
    "tone",
    "iteration",
    "risk_auto_write",
    "risk_auto_exec",
    "risk_auto_send",
}


def test_profile_schema_drives_form(client):
    """字段表由后端下发 —— 前端表单不硬编码字段（改后端即改表单）。"""
    d = client.get("/v9/pa/profile/schema").get_json()
    assert d["ok"] and set(d["fields"]) == FIELD_KEYS
    assert d["fields"]["industry"]["options"] and d["fields"]["industry"]["domain"] == "fact"
    # order: Flask jsonify 默认按 key 排序, 表单语义顺序必须显式下发
    assert d["order"][0] == "industry" and d["order"][-1] == "risk_auto_send"
    # 缺省保守：未声明 -> 不允许自动
    assert d["switches"]["auto_write"] is False and d["switches"]["detail"] == "中"


def test_profile_write_lands_and_drives_switches(client):
    r = client.post(
        "/v9/pa/profile",
        json={"source": "form", "values": {"industry": "光电", "report_detail": "详", "risk_auto_write": "是"}},
    )
    d = r.get_json()
    assert d["ok"] and len(d["written"]) == 3
    assert d["switches"] == {"auto_write": True, "auto_exec": False, "auto_send": False, "detail": "详"}
    vals = client.get("/v9/pa/profile/schema").get_json()["values"]
    assert vals["industry"] == "光电" and vals["risk_auto_write"] == "是"


def test_profile_write_rejects_bad_value_and_is_idempotent(client):
    bad = client.post("/v9/pa/profile", json={"values": {"industry": "造车"}}).get_json()
    assert bad["ok"] and not bad["written"]
    assert bad["rejected"][0]["key"] == "industry" and "不在选项内" in bad["rejected"][0]["reason"]
    client.post("/v9/pa/profile", json={"values": {"tone": "直接"}})
    again = client.post("/v9/pa/profile", json={"values": {"tone": "直接"}}).get_json()
    assert not again["written"] and again["unchanged"][0]["key"] == "tone"


def test_profile_write_needs_values(client):
    r = client.post("/v9/pa/profile", json={})
    assert r.status_code == 400 and not r.get_json()["ok"]


def test_profile_correction_keeps_supersedes_chain(client):
    """老板改口 = 旧条目标 revised + 新条目 supersedes 指向旧 id（链=训练标注）。"""
    import os

    from core.pa.profile import ProfileStore

    a = client.post("/v9/pa/profile", json={"values": {"industry": "光电"}}).get_json()
    first = a["written"][0]["entry_id"]
    b = client.post("/v9/pa/profile", json={"values": {"industry": "制造"}}).get_json()
    assert b["written"][0]["superseded"] == first
    st = ProfileStore(os.path.join(os.environ["PA_DATA_DIR"], "profile.json"))
    by_id = {e["id"]: e for e in st.entries}
    assert by_id[first]["status"] == "revised"
    assert by_id[b["written"][0]["entry_id"]]["supersedes"] == first


def test_dialog_collects_fields_and_recaps(client):
    """聊天层收集：说到字段 -> 落库 + 复述一句让老板当场纠正。"""
    d = client.post("/v9/pa/dialog", json={"session_id": "s20", "text": "我是做光电的，汇报详细一点"}).get_json()
    assert d["ok"]
    assert {w["key"] for w in d["collected"]["written"]} == {"industry", "report_detail"}
    assert "记下了" in d["reply"] and "行业 = 光电" in d["reply"]
    vals = client.get("/v9/pa/profile/schema").get_json()["values"]
    assert vals["industry"] == "光电"


def test_dialog_without_fields_does_not_recap(client):
    d = client.post("/v9/pa/dialog", json={"session_id": "s21", "text": "今天天气不错"}).get_json()
    assert d["collected"]["written"] == [] and "记下了" not in d["reply"]
