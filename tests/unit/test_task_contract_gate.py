# -*- coding: utf-8 -*-
"""2026-09-09 F0.2a: phase gate — 契约阶段覆盖关键词裁决/注册表/工具闸"""
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


def test_bind_and_load(env):
    c = tc.new_contract("tA", nodes=[{"id": "n1"}])
    tc.save(c)
    tc.bind_session("s1", "tA")
    got = tc.contract_for_session("s1")
    assert got and got["task_id"] == "tA"
    assert tc.contract_for_session("s_unknown") is None


def test_research_phase_does_not_require_final_write(env):
    c = tc.new_contract("tR", nodes=[{"id": "v", "done_when": ["x"]}])
    c["phase"] = "researching"
    tc.save(c)
    tc.bind_session("sR", "tR")
    assert tc.should_require_final_write("sR") is False
    assert tc.contract_for_session("s_no") is None  # 无契约 → 上层沿用旧逻辑(None)


def test_drafting_phase_requires_final_write(env):
    c = tc.new_contract("tD", nodes=[{"id": "d", "artifact_spec": {"path": "x.md"}}])
    c["phase"] = "drafting"
    tc.save(c)
    tc.bind_session("sD", "tD")
    assert tc.should_require_final_write("sD") is True


def test_phase_gate_verifying_blocks_research_tools(env):
    c = tc.new_contract("tV", nodes=[])
    c["phase"] = "verifying"
    ok, steer = tc.phase_gate(c, "web_search")
    assert ok is False and steer and "verifying" in steer
    ok2, _ = tc.phase_gate(c, "read_file")
    assert ok2 is True


def test_phase_gate_research_allows_all(env):
    c = tc.new_contract("tX", nodes=[])
    c["phase"] = "researching"
    assert tc.phase_gate(c, "fetch_web")[0] is True


def test_waiting_user_payload(env):
    c = tc.new_contract("tW", nodes=[{"id": "ask", "phase": "waiting_user"}])
    c["phase"] = "waiting_user"
    c["checkpoint"] = {"question": "视觉风格?", "options": ["工业风"]}
    tc.save(c)
    tc.bind_session("sW", "tW")
    p = tc.waiting_user_payload("sW")
    assert p and p["status"] == "waiting_user" and "风格" in p["question"]
    assert tc.waiting_user_payload("s_no") is None
