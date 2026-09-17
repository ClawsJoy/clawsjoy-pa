# -*- coding: utf-8 -*-
"""2026-09-09 F0.5: 单一完成裁决"""
import sys

sys.path.insert(0, ".")
import pytest

import core.gateway.task_contract as tc


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(tc, "_CONTRACTS_DIR", tmp_path)
    monkeypatch.setattr(tc, "_INDEX_FILE", tmp_path / "_index.json")
    monkeypatch.setattr(tc, "_session_index", {})
    yield


def test_no_contract_legacy(env):
    assert tc.decide_completion(None, True) == (None, None)
    assert tc.contract_should_complete(None) is False


def test_contract_artifact_fail_no_complete(env):
    msg = "先核实4项政策，再确认视觉风格，最后生成PPT保存到 data/reports/x.md"
    c = tc.ensure_contract("sF", "tF", msg)
    for i in range(4):
        c, _ = tc.dispatch(
            "tF", c, tc.evidence_updated("c%d" % i, "verified" if i < 3 else "unverifiable", terminal=True)
        )
    c, _ = tc.dispatch("tF", c, tc.node_done("verify"))
    c, _ = tc.dispatch("tF", c, tc.user_answer("工业风"))
    assert c["phase"] == "drafting"
    c2, _ = tc.decide_completion(c, False, "缺页")
    assert tc.contract_should_complete(c2) is False
    c3, _ = tc.decide_completion(c2, True, "ok", {"path": "data/reports/x.md"})
    assert tc.contract_should_complete(c3) is True


def test_full_flow_single_decision(env):
    msg = "先核实4项政策，再确认视觉风格，最后生成PPT保存到 data/reports/x.md"
    c = tc.ensure_contract("sG", "tG", msg)
    for i in range(4):
        c, _ = tc.dispatch(
            "tG", c, tc.evidence_updated("c%d" % i, "verified" if i < 3 else "unverifiable", terminal=True)
        )
    c, _ = tc.dispatch("tG", c, tc.node_done("verify"))
    assert c["phase"] == "waiting_user"
    c, _ = tc.dispatch("tG", c, tc.user_answer("工业风"))
    assert c["phase"] == "drafting"
    c2, _ = tc.decide_completion(c, True, "ok")
    assert tc.contract_should_complete(c2) is True
