# -*- coding: utf-8 -*-
"""Execution Contract 层测试：**单一完成裁决**（假成交红线）+ 进度分子分母同源。"""

from __future__ import annotations

import pytest

from core.pes import contract as ct


def _c(**kw):
    c = ct.new_contract("t-1", objective="目标")
    c.update(kw)
    return c


def test_upgrade_空契约返回空():
    assert ct.upgrade(None) == {}


def test_upgrade_空字典补齐为整份默认字段():
    """回归：``upgrade({})`` 曾返回 ``{}``，导致 ``new_run_fields`` 直接 KeyError。"""
    c = ct.upgrade({})
    for k in ct.CONTRACT_DEFAULTS:
        assert k in c


def test_upgrade_幂等且不覆盖已有值():
    c = ct.upgrade({"task_id": "t", "steps_total": 7})
    again = ct.upgrade(c)
    assert again["steps_total"] == 7
    assert again["task_id"] == "t"
    assert ct.upgrade(again) == again


def test_new_contract_补齐全部字段():
    c = ct.new_contract("t-1")
    for k in ct.CONTRACT_DEFAULTS:
        assert k in c
    assert ct.validate(c) == []


def test_无产物事实_永不_done():
    v = ct.verdict(_c(done_when_status="verified", artifact={"exists": False}))
    assert v["state"] == "not_done"
    assert v["reason"] == "no_artifact_fact"
    assert v["next_action"]


def test_claimed_不算完成():
    c = ct.mark_claimed(_c(), done_when="产出报告")
    assert c["done_when_status"] == "claimed"
    v = ct.verdict(c, {"exists": True})
    assert v["state"] == "not_done"
    assert v["reason"] == "claimed_only"


def test_mark_claimed_永不动_verified():
    c = _c(done_when_status="verified", artifact_verified_by="pa")
    assert ct.mark_claimed(c)["done_when_status"] == "verified"


def test_record_artifact_的_exists_由磁盘实况决定(tmp_path):
    missing = ct.record_artifact(_c(), str(tmp_path / "nope.txt"))
    assert missing["artifact"]["exists"] is False
    real = tmp_path / "out.txt"
    real.write_text("done", encoding="utf-8")
    got = ct.record_artifact(_c(), str(real))
    assert got["artifact"]["exists"] is True
    assert got["artifact"]["bytes"] == 4


def test_完整快乐路径才_done(tmp_path):
    out = tmp_path / "deliverable.md"
    out.write_text("# 交付", encoding="utf-8")
    c = ct.record_artifact(_c(), str(out), kind="report", verified_by="pa.reviewer")
    v = ct.verdict(c)
    assert v["state"] == "done"
    assert v["verified_by"] == "pa.reviewer"


def test_done_when_未设置时给出可读下一步():
    v = ct.verdict(_c(artifact={"exists": True}))
    assert v["state"] == "not_done"
    assert v["reason"] == "done_when_unset"


def test_无契约时不裁决():
    assert ct.verdict(None)["reason"] == "no_contract"


def test_进度分母未声明则不显示百分比():
    p = ct.progress(_c(steps_total=0))
    assert p["mismatch"] is True
    assert "percent" not in p


def test_进度分子分母同源才给百分比():
    p = ct.progress(_c(steps_total=4, steps_done=1))
    assert p["mismatch"] is False and p["percent"] == 25.0


def test_进度不同源则标红不取平均():
    p = ct.progress(_c(steps_total=4, steps_done=1), reported_done=3)
    assert p["mismatch"] is True
    assert "percent" not in p
    assert p["reported_done"] == 3


def test_幂等键稳定且随输入变化():
    a = ct.idempotency_key("r1", ct.digest_task("任务"))
    assert a == ct.idempotency_key("r1", ct.digest_task("任务"))
    assert a != ct.idempotency_key("r2", ct.digest_task("任务"))


def test_字段写权归属():
    assert ct.ownership_of("artifact") == "execution"
    assert ct.ownership_of("steps_done") == "execution"
    assert ct.ownership_of("artifact_verified_by") == "summary"
    assert ct.ownership_of("不存在") == "unknown"


def test_执行态与汇总态字段不重叠():
    assert not set(ct.EXECUTION_FIELDS) & set(ct.SUMMARY_FIELDS)


def test_validate_报空契约():
    assert ct.validate(None) == ["契约为空"]


def test_new_run_fields_标记写者是_v9():
    f = ct.new_run_fields("r1", "任务", 3)
    assert f["recorded_by"] == "v9"
    assert f["steps_total"] == 3 and f["idempotency_key"]
