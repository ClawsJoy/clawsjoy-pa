# -*- coding: utf-8 -*-
"""Run Registry（汇总态）测试：**PA 不代填** + 假成交判据 + 对账三态。"""

from __future__ import annotations

import json
from pathlib import Path

from core.pes.run_registry import PA_OWNED_FIELDS, SOURCE_OWNED_FIELDS, RunRegistry


def _rr(pes_dir):
    return RunRegistry(pes_dir / "runs.jsonl")


def _rows(rr):
    return [
        json.loads(x)
        for x in rr.path.read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]


def test_登记一次运行(pes_dir):
    r = _rr(pes_dir)
    assert r.register_run("r1")["state"] == "running"
    assert r.has("r1") is True


def test_未登记的_run_返回_None(pes_dir):
    assert _rr(pes_dir).get("nope") is None


def test_PA_独占字段不得由来源回报覆盖(pes_dir):
    """状态所有权硬边界：``artifact_verified_by`` 是 PA 独占写的。"""
    r = _rr(pes_dir)
    r.register_run("r1")
    r.update_from_source("r1", {"artifact_verified_by": "自称的"})
    assert r.get("r1")["artifact_verified_by"] == ""
    rejected = [x for x in _rows(r) if x["kind"] == "fields_rejected"]
    assert rejected and "artifact_verified_by" in rejected[0]["fields"]["rejected"]


def test_越界字段被丢弃并留痕(pes_dir):
    r = _rr(pes_dir)
    r.register_run("r1")
    r.update_from_source("r1", {"bogus_field": 1, "steps_done": 2})
    assert r.get("r1")["steps_done"] == 2
    rejected = [x for x in _rows(r) if x["kind"] == "fields_rejected"]
    assert "bogus_field" in rejected[0]["fields"]["rejected"]


def test_非法状态值被拒(pes_dir):
    r = _rr(pes_dir)
    r.register_run("r1")
    r.update_from_source("r1", {"state": "我完成了"})
    assert r.get("r1")["state"] == "running"


def test_独立复验必须留验证者身份(pes_dir):
    r = _rr(pes_dir)
    r.register_run("r1")
    import pytest

    with pytest.raises(ValueError):
        r.verify_artifact("r1", "")


def test_复验写入验证者(pes_dir):
    r = _rr(pes_dir)
    r.register_run("r1")
    assert r.verify_artifact("r1", "pa.reviewer")["artifact_verified_by"] == "pa.reviewer"


def test_声称完成但无产物被机械标出(pes_dir):
    r = _rr(pes_dir)
    r.register_run("r1", state="done")
    bad = r.incomplete_claims()
    assert [b["run_id"] for b in bad] == ["r1"]
    assert "无产物事实" in bad[0]["reason"]


def test_有产物事实的_done_不算假成交(pes_dir):
    r = _rr(pes_dir)
    r.register_run("r1", state="done", artifact={"exists": True, "path": "x"})
    assert r.incomplete_claims() == []


def test_仅_claimed_的_done_被标出(pes_dir):
    r = _rr(pes_dir)
    r.register_run("r1", state="done", done_when_status="claimed", artifact={"exists": True})
    assert any("claimed" in b["reason"] for b in r.incomplete_claims())


def test_未结运行可查(pes_dir):
    r = _rr(pes_dir)
    r.register_run("r1", state="running")
    r.register_run("r2", state="done")
    assert [d["run_id"] for d in r.open_runs()] == ["r1"]


# ---------------------------------------------------------------- 对账三态
def test_对账_来源有而注册表无(pes_dir):
    out = _rr(pes_dir).reconcile("r1", {"state": "done"})
    assert out["result"] == "registry_missing"


def test_对账_注册表有而来源丢失(pes_dir):
    r = _rr(pes_dir)
    r.register_run("r1")
    assert r.reconcile("r1", None)["result"] == "source_missing"


def test_对账_一致(pes_dir):
    r = _rr(pes_dir)
    r.register_run("r1", state="running")
    out = r.reconcile("r1", {"state": "running"})
    assert out["result"] == "consistent"


def test_对账_不一致必须列出差异(pes_dir):
    r = _rr(pes_dir)
    r.register_run("r1", state="running")
    out = r.reconcile("r1", {"state": "done"})
    assert out["result"] == "inconsistent"
    assert out["differences"] and out["warning"]


def test_对账不一致写审计告警(pes_dir):
    from core.pes.audit import audit_log

    r = _rr(pes_dir)
    r.register_run("r1", state="running")
    r.reconcile("r1", {"state": "done"})
    kinds = [x["kind"] for x in audit_log().for_run("r1")]
    assert "registry.reconcile_inconsistent" in kinds


# ---------------------------------------------------------------- 链与所有权
def test_汇总态是追加式且链完整(pes_dir):
    r = _rr(pes_dir)
    r.register_run("r1")
    r.update_from_source("r1", {"steps_done": 1})
    assert r.verify_chain()["ok"] is True
    assert len(_rows(r)) >= 2


def test_篡改汇总态被检出(pes_dir):
    r = _rr(pes_dir)
    r.register_run("r1")
    r.update_from_source("r1", {"steps_done": 1})
    lines = r.path.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[1])
    row["fields"]["steps_done"] = 99
    lines[1] = json.dumps(row, ensure_ascii=False)
    r.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert r.verify_chain()["ok"] is False


def test_执行态与汇总态字段集不重叠():
    assert set(PA_OWNED_FIELDS) & set(SOURCE_OWNED_FIELDS) == set()
    assert PA_OWNED_FIELDS == ("artifact_verified_by",)


def test_汇总态记账本身走唯一出口(pes_dir):
    from core.pes.state_integrity import scan_state_dir

    r = _rr(pes_dir)
    r.register_run("r1")
    # runs.jsonl 是追加式账本（靠哈希链），**不应**出现在「未插桩」清单里
    assert [Path(b["path"]).name for b in scan_state_dir(pes_dir, scope="all")] == []
