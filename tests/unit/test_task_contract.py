# -*- coding: utf-8 -*-
"""2026-09-09 F0 TaskContract 内核纯 reducer 单测"""
import sys

sys.path.insert(0, ".")
import pytest

import core.gateway.task_contract as tc


def _contract(nodes=None):
    return tc.new_contract(
        "t1",
        "先核实政策再生成PPT",
        nodes=nodes
        or [
            {"id": "verify", "depends_on": [], "done_when": ["opc-reward"]},
            {"id": "ask_style", "depends_on": ["verify"], "phase": "waiting_user", "ask": "PPTX 视觉风格?"},
            {
                "id": "gen",
                "depends_on": ["ask_style"],
                "done_when": ["artifact out.pptx"],
                "artifact_spec": {"path": "out.pptx"},
            },
        ],
    )


def test_reducer_pure_no_mutation():
    c = _contract()
    c2, _ = tc.reduce(c, tc.evidence_updated("opc-reward", "unverifiable", terminal=True))
    assert c["phase"] == "planned"  # 入参不变
    assert c2["phase"] == "researching"
    assert c2["evidence"]["opc-reward"]["terminal"] is True


def test_terminal_evidence_is_valid_conclusion():
    """terminal=true 证据满足 done_when(公开渠道无法验证是正确结论)"""
    c = _contract()
    c, _ = tc.dispatch("t1", c, tc.evidence_updated("opc-reward", "unverifiable", terminal=True, attempts=2))
    assert c["phase"] == "researching"
    # 节点推进: 证据满足 → verify 完成 → 进入 waiting_user
    c, eff = tc.dispatch("t1", c, tc.node_done("verify"))
    assert c["phase"] == "waiting_user"
    assert any(e["kind"] == "ask_user" for e in eff)


def test_waiting_user_no_auto_continue():
    c, _ = tc.dispatch("t1", _contract(), tc.evidence_updated("opc-reward", "verified"))
    c, eff = tc.dispatch("t1", c, tc.node_done("verify"))
    assert c["phase"] == "waiting_user"
    c2, eff2 = tc.dispatch("t1", c, tc.note("继续"))  # 无 request_user 事件不得离开 waiting_user
    assert c2["phase"] == "waiting_user"


def test_completed_only_via_artifact_ok():
    c = _contract()
    c, _ = tc.dispatch("t1", c, tc.evidence_updated("opc-reward", "verified"))
    c, _ = tc.dispatch("t1", c, tc.node_done("verify"))
    c, eff = tc.dispatch("t1", c, tc.request_user("风格?", ["工业风"]))
    assert c["phase"] == "waiting_user"
    # 用户答复 → 完成 waiting_user 节点 → 推进到 gen(drafting)
    c, _ = tc.dispatch("t1", c, tc.user_answer("工业风"))
    assert c["phase"] == "drafting", c["phase"]
    # 校验不通过 → 不完成
    c2, _ = tc.dispatch("t1", c, tc.artifact_verified(False, "缺 P9-P15"))
    assert c2["phase"] != "completed"
    # 校验通过 → completed
    c3, eff3 = tc.dispatch("t1", c2, tc.artifact_verified(True, "ok", {"path": "out.pptx"}))
    assert c3["phase"] == "completed"
    assert any(e["kind"] == "completed" for e in eff3)


def test_persistence_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(tc, "_CONTRACTS_DIR", tmp_path)
    c = _contract()
    p = tc.save(c)
    assert p and tmp_path.joinpath("t1.json").exists()
    c2 = tc.load("t1")
    assert c2["task_id"] == "t1"


def test_phase_helpers():
    assert tc.phase_is_research("researching") and tc.phase_is_research("planned")
    assert tc.phase_allows_final_write("drafting")
    assert not tc.phase_allows_final_write("researching")
