# -*- coding: utf-8 -*-
"""X-16 批 B/C（DS 2026-09-18 拍）：`permission` / `decision` 接统一出口；`grants` 补审计留痕。

【反例证明（改前必假）】本文件跑在接线前的 HEAD 上必须大面积红：
  · HEAD 的 `PermissionStore.load()` 对「损坏 JSON／非法 level／空文件」**静默回落默认档**
    ⇒「抛」「零写入」不成立（且 `只读 < 标准` ⇒ 损坏即**放宽**）；
  · HEAD 的 `DecisionStore.load()` 静默回落 `{"decisions": []}`；
  · HEAD 的 `grants._save()` **无审计留痕**；
  · HEAD 的 `/v9/pa/permission` 在坏状态下回 **200**（而不是 409 可读提示）。
  实测：HEAD ⇒ 8 failed / 3 passed（3 passed 是刻意保留的护栏）。
"""
import json
from pathlib import Path

import pytest
from flask import Flask

from core.pa.state_out import PAStateCorrupt


# ============================================================ permission
def test_permission_损坏_抛且零写入(tmp_path):
    from core.pa.permission import PermissionStore

    p = tmp_path / "permission.json"
    p.write_text("{ 半截", encoding="utf-8")
    bad = p.read_bytes()

    with pytest.raises(PAStateCorrupt):
        PermissionStore(str(p))

    assert p.read_bytes() == bad


def test_permission_非法level_抛且零写入(tmp_path):
    """**静默放宽的对治点**：非法取值此前被忽略 ⇒ 回落 `标准`（比 `只读` 宽）。"""
    from core.pa.permission import PermissionStore

    p = tmp_path / "permission.json"
    p.write_text(json.dumps({"level": "完全放行"}), encoding="utf-8")
    bad = p.read_bytes()

    with pytest.raises(PAStateCorrupt):
        PermissionStore(str(p))

    assert p.read_bytes() == bad


def test_permission_写走出口_留写者台账(tmp_path):
    from core.pa.permission import PermissionStore

    p = tmp_path / "permission.json"
    r = PermissionStore(str(p)).set("只读", user_id="boss")

    assert r.get("ok") is True and r.get("level") == "只读"
    log = p.with_name("permission.json.writes.jsonl")
    assert log.exists(), "接统一出口后必须留写者归属台账"
    assert json.loads(log.read_text(encoding="utf-8").splitlines()[-1])["writer"] == "core/pa/permission.py"
    assert json.loads(p.read_text(encoding="utf-8"))["level"] == "只读"


def test_permission_不存在_默认档不抛(tmp_path):
    """护栏：不存在 ≠ 损坏（首次运行正常）。"""
    from core.pa.permission import DEFAULT_LEVEL, PermissionStore

    assert PermissionStore(str(tmp_path / "nope.json")).get() == DEFAULT_LEVEL


def test_permission_非法取值_set_拒绝(tmp_path):
    """护栏：白名单以外的取值仍被 `set()` 拒（既有行为不许漂）。"""
    from core.pa.permission import PermissionStore

    r = PermissionStore(str(tmp_path / "permission.json")).set("完全放行")
    assert r.get("ok") is False and "权限档必须是" in r.get("error", "")


# ============================================================ decision
def test_decision_损坏_抛(tmp_path):
    from core.pa.decision import DecisionStore

    d = tmp_path / "pa"
    d.mkdir()
    p = d / "decision_log.json"
    p.write_text("{ 半截", encoding="utf-8")
    bad = p.read_bytes()

    with pytest.raises(PAStateCorrupt):
        DecisionStore(str(d)).load()

    assert p.read_bytes() == bad


def test_decision_结构不符_抛(tmp_path):
    from core.pa.decision import DecisionStore

    d = tmp_path / "pa"
    d.mkdir()
    p = d / "decision_log.json"
    p.write_text(json.dumps({"decisions": "oops"}), encoding="utf-8")
    bad = p.read_bytes()

    with pytest.raises(PAStateCorrupt):
        DecisionStore(str(d)).load()

    assert p.read_bytes() == bad


def test_decision_record_留写者台账(tmp_path):
    from core.pa.decision import DecisionStore

    d = tmp_path / "pa"
    st = DecisionStore(str(d))
    st.record("u1", "s1", "node", "评审", "采纳", note="ok")

    log = d / "decision_log.json.writes.jsonl"
    assert log.exists()
    assert json.loads(log.read_text(encoding="utf-8").splitlines()[-1])["writer"] == "core/pa/decision.py"
    assert len(json.loads((d / "decision_log.json").read_text(encoding="utf-8"))["decisions"]) == 1


def test_decision_record_追加不清历史(tmp_path):
    """护栏：两次 record ⇒ 两条都在（接出口不得把「追加」变成「覆盖」）。"""
    from core.pa.decision import DecisionStore

    d = tmp_path / "pa"
    st = DecisionStore(str(d))
    st.record("u1", "s1", "n", "评审", "采纳")
    st.record("u1", "s1", "n", "交付", "退回")

    assert [x["decision"] for x in st.list()] == ["采纳", "退回"]


# ============================================================ grants（B1：只加审计）
def test_grants_写_留审计留痕(tmp_path, monkeypatch):
    from core.pa import grants as G

    monkeypatch.setattr(G, "grants_path", lambda: tmp_path / "grants.yaml")
    audit_file = tmp_path / "audit.jsonl"
    from core.pes import audit as A

    monkeypatch.setattr(A, "audit_log", lambda path=None: A.AuditLog(audit_file))

    ok = G._save({"version": 1, "grants": [{"scene": "§execute_command§|mkdir"}]})

    assert ok is True and (tmp_path / "grants.yaml").exists()
    rows = [json.loads(x) for x in audit_file.read_text(encoding="utf-8").splitlines() if x.strip()]
    hits = [r for r in rows if r.get("kind") == "pa.grants.write"]
    assert hits, "grants 写入必须留审计（B1）"
    assert hits[-1]["payload"]["ok"] is True and hits[-1]["payload"]["grants_n"] == 1


# ============================================================ 路由：可读提示
def test_路由_状态不可用_409可读提示_不外泄traceback(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    Path(str(tmp_path / "pa")).mkdir(parents=True, exist_ok=True)
    Path(str(tmp_path / "pa" / "permission.json")).write_text("{ 半截", encoding="utf-8")

    app = Flask(__name__)
    from core.pa.gateway_routes import register_pa_routes

    register_pa_routes(app)
    r = app.test_client().get("/v9/pa/permission")

    assert r.status_code == 409, "坏状态不得回 200（假绿），也不得漏成 HTML 500"
    assert r.is_json, "必须是 JSON（前端 if(r.ok) 依赖形状）"
    d = r.get_json()
    assert d["ok"] is False and d["error"] == "pa_state_corrupt"
    assert d.get("message"), "必须给可读提示"
    assert d.get("hint")
    assert "Traceback" not in json.dumps(d, ensure_ascii=False)
