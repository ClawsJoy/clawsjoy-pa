# -*- coding: utf-8 -*-
"""2026-09-09 F0.2b E2E: 编译→核实→waiting_user→答复→生成→artifact→completed"""
import sys

sys.path.insert(0, ".")
import pytest

import core.gateway.task_contract as tc


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(tc, "_CONTRACTS_DIR", tmp_path)
    monkeypatch.setattr(tc, "_INDEX_FILE", tmp_path / "_index.json")
    monkeypatch.setattr(tc, "_session_index", {})
    yield tmp_path


def test_compile_full_chain(env):
    msg = "先核实政策4项(10%奖励/8大行业/揭榜申报/1300亿基金群)，再确认视觉风格，最后生成PPT大纲并保存到 data/reports/opc.md"
    c = tc.compile_contract("tE2E", msg)
    assert c is not None
    ids = [n["id"] for n in c["nodes"]]
    assert ids == ["verify", "ask_style", "gen"]
    assert tc.contract_for_session("sE2E") is None  # 未绑定
    c2 = tc.ensure_contract("sE2E", "tE2E", msg)
    assert c2 and tc.contract_for_session("sE2E") is not None


def test_e2e_research_wait_draft_complete(env):
    msg = "先核实4项政策，再确认视觉风格，最后生成PPT保存到 data/reports/opc.md"
    c = tc.ensure_contract("sE", "tE", msg)
    # 核实证据 4 项(terminal/unverified 亦算已分类)
    for i in range(4):
        c, _ = tc.dispatch(
            "tE",
            c,
            tc.evidence_updated("claim%d" % i, "verified" if i < 3 else "unverifiable", terminal=(i == 3), attempts=2),
        )
    # verify 完成 → ask_style(waiting_user)
    c, eff = tc.dispatch("tE", c, tc.node_done("verify"))
    assert c["phase"] == "waiting_user", c["phase"]
    assert any(e["kind"] == "ask_user" for e in eff)
    # 用户答复 → gen(drafting)
    c, _ = tc.dispatch("tE", c, tc.user_answer("工业科技风"))
    assert c["phase"] == "drafting", c["phase"]
    # 产物校验通过 → completed
    c, eff2 = tc.dispatch("tE", c, tc.artifact_verified(True, "ok", {"path": "data/reports/opc.md"}))
    assert c["phase"] == "completed", c["phase"]
    assert any(e["kind"] == "completed" for e in eff2)


def test_compile_failure_fallback_none(env):
    assert tc.compile_contract("tX", "随便聊聊") is None
