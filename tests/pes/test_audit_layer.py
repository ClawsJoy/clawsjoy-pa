# -*- coding: utf-8 -*-
"""Audit 层测试：独立追加流 + 哈希链 + **run_id 是资格位**。"""

from __future__ import annotations

import json

import pytest

from core.pes.audit import GENESIS, AuditLog, chain_hash


def _log(tmp_path, name="audit.jsonl"):
    return AuditLog(tmp_path / name)


def test_缺_run_id_的条目不合格(tmp_path):
    log = _log(tmp_path)
    row = log.record("state.read", payload={"k": 1})
    assert row["qualified"] is False
    assert [r["kind"] for r in log.unqualified()] == ["state.read"]


def test_record_for_run_拒绝空_run_id(tmp_path):
    log = _log(tmp_path)
    with pytest.raises(ValueError):
        log.record_for_run("done", "")


def test_for_run_只取该_run_的条目(tmp_path):
    log = _log(tmp_path)
    log.record_for_run("a", "r1")
    log.record_for_run("b", "r2")
    log.record_for_run("c", "r1")
    assert [r["kind"] for r in log.for_run("r1")] == ["a", "c"]


def test_哈希链逐行可验(tmp_path):
    log = _log(tmp_path)
    log.record_for_run("a", "r1")
    log.record_for_run("b", "r1")
    v = log.verify_chain()
    assert v["ok"] is True and v["rows"] == 2


def test_篡改被检出并定位到序号(tmp_path):
    log = _log(tmp_path)
    log.record_for_run("a", "r1")
    log.record_for_run("b", "r1")
    lines = log.path.read_text(encoding="utf-8").splitlines()
    bad = json.loads(lines[1])
    bad["kind"] = "改过了"  # 篡改第二行
    lines[1] = json.dumps(bad, ensure_ascii=False)
    log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    v = log.verify_chain()
    assert v["ok"] is False
    assert v["first_bad_seq"] == 2


def test_审计流与执行态分文件(tmp_path):
    """总任务书 §3.1：审计是**独立**流，查询审计不依赖执行态。"""
    log = _log(tmp_path)
    log.record_for_run("a", "r1")
    assert log.path.name == "audit.jsonl"
    assert log.path.exists()
    assert log._last_hash() != GENESIS


def test_链起点是_GENESIS_且首行_prev_hash_指向它(tmp_path):
    log = _log(tmp_path)
    row = log.record_for_run("a", "r1")
    assert row["prev_hash"] == GENESIS


def test_写入失败不打断业务但标降级(tmp_path):
    """审计失败不得让业务崩 —— 但必须在行内标 ``degraded``（不静默）。"""
    log = AuditLog(tmp_path)  # 指向目录 ⇒ 写入必然失败
    row = log.record_for_run("a", "r1")
    assert row["degraded"].startswith("audit write failed")


def test_stats_汇总(tmp_path):
    log = _log(tmp_path)
    log.record_for_run("a", "r1")
    log.record("b")
    s = log.stats()
    assert s["rows"] == 2 and s["qualified"] == 1 and s["unqualified"] == 1
    assert s["chain"] is True


def test_chain_hash_是两条账本共用的同一构造():
    row = {"seq": 1, "kind": "x"}
    assert chain_hash(GENESIS, row) == chain_hash(GENESIS, dict(row))
    assert chain_hash(GENESIS, row) != chain_hash("1" * 64, row)


def test_坏行被跳过不炸(tmp_path):
    log = _log(tmp_path)
    log.record_for_run("a", "r1")
    with open(log.path, "a", encoding="utf-8") as f:
        f.write("这不是 JSON\n")
    assert log.verify_chain()["ok"] is True
    assert len(log.tail(10)) == 1
