# -*- coding: utf-8 -*-
"""2026-09-09: 首轮 auto-bind + goal↔contract 绑定校验"""
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


def test_first_round_autobind_chain(env):
    c, bound = tc.first_round_autobind("sA", "tA", "先核实4项政策，再确认风格，最后生成PPT保存到 data/reports/x.md")
    assert bound and c and len(c["nodes"]) >= 2
    assert tc.contract_for_session("sA") is not None


def test_first_round_autobind_single_no_bind(env):
    c, bound = tc.first_round_autobind("sB", "tB", "生成一份报告保存到 data/reports/r.md")
    assert bound is False and c is None
    assert tc.contract_for_session("sB") is None


def test_first_round_chat_no_bind(env):
    assert tc.first_round_autobind("sC", "tC", "随便聊聊") == (None, False)


def test_binding_mismatch(env):
    c = tc.new_contract("tD", objective="先核实宁波政策再生成PPT")
    assert tc.binding_mismatch("做封面任务", c) is True
    assert tc.binding_mismatch("先核实宁波政策再生成PPT", c) is False
    assert tc.binding_mismatch("核实宁波政策并生成PPT", c) is False
    assert tc.binding_mismatch("xxx", None) is False
