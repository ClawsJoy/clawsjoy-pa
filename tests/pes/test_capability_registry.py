# -*- coding: utf-8 -*-
"""Capability Registry 层测试：**未注册即拒绝**（fail-closed）+ 风险分层门禁。"""

from __future__ import annotations

import pytest

from core.pes.capability_registry import RISK_LEVELS, CapabilityRegistry


def _reg(pes_dir):
    return CapabilityRegistry(pes_dir / "capabilities.json")


def test_种子能力幂等(pes_dir):
    r = _reg(pes_dir)
    assert r.ensure_seeded() == 12
    assert r.ensure_seeded() == 0


def test_未注册即拒绝(pes_dir):
    r = _reg(pes_dir)
    r.ensure_seeded()
    assert r.is_registered("nope") is False
    with pytest.raises(PermissionError):
        r.require("nope")


def test_gate_for_未注册也拒绝(pes_dir):
    """不得对未注册能力返回「宽松默认值」。"""
    with pytest.raises(PermissionError):
        _reg(pes_dir).gate_for("nope")


def test_注册默认取最保守(pes_dir):
    r = _reg(pes_dir)
    rec = r.register("brand_new")
    assert rec["risk_level"] == "R3"
    assert rec["requires_grant"] is True
    assert r.gate_for("brand_new")["approval_required"] is True


def test_注册即受管_立刻可查(pes_dir):
    r = _reg(pes_dir)
    r.register("read_only_thing", risk_level="R0", requires_grant=False)
    g = r.gate_for("read_only_thing")
    assert g["risk_level"] == "R0" and g["approval_required"] is False


def test_非法风险等级报_ValueError(pes_dir):
    """回归：``"..." % x, y`` 的优先级坑 —— 必须抛 ValueError 而不是 TypeError。"""
    with pytest.raises(ValueError):
        _reg(pes_dir).register("bad", risk_level="R9")


def test_四档风险都存在且门禁不同():
    assert set(RISK_LEVELS) == {"R0", "R1", "R2", "R3"}
    assert RISK_LEVELS["R0"]["approval_required"] is False
    assert RISK_LEVELS["R1"]["approval_required"] is False
    assert RISK_LEVELS["R2"]["approval_required"] is True
    assert RISK_LEVELS["R3"]["approval_required"] is True
    assert RISK_LEVELS["R2"]["window_s"] == 120
    assert RISK_LEVELS["R3"]["window_s"] == 900


def test_种子能力覆盖四档(pes_dir):
    r = _reg(pes_dir)
    r.ensure_seeded()
    for lvl in ("R0", "R1", "R2", "R3"):
        assert r.by_risk(lvl), "种子能力缺 %s 档" % lvl


def test_不可逆动作带撤销窗口(pes_dir):
    r = _reg(pes_dir)
    r.ensure_seeded()
    assert r.gate_for("publish")["window_s"] == 900
    assert r.gate_for("send_message")["window_s"] == 120
    assert r.gate_for("read_file")["window_s"] == 0


def test_注销后立即回到未注册即拒绝(pes_dir):
    r = _reg(pes_dir)
    r.register("temp_cap", risk_level="R0", requires_grant=False)
    assert r.unregister("temp_cap") is True
    assert r.is_registered("temp_cap") is False
    with pytest.raises(PermissionError):
        r.require("temp_cap")


def test_list_按风险等级排序(pes_dir):
    r = _reg(pes_dir)
    r.ensure_seeded()
    levels = [c["risk_level"] for c in r.list()]
    assert levels == sorted(levels)


def test_注册表本身也走状态唯一出口(pes_dir):
    """dogfooding：能力注册表不许裸写 JSON。"""
    from core.pes.state_integrity import detect_uninstrumented

    r = _reg(pes_dir)
    r.ensure_seeded()
    assert detect_uninstrumented(pes_dir / "capabilities.json")["instrumented"] is True
