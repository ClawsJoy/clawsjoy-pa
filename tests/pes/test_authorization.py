# -*- coding: utf-8 -*-
"""Authorization 层测试：**两套授权 + 转换层**、撤销优先、可解释的拒绝。"""

from __future__ import annotations

import pytest

from core.pes.authorization import (
    ALLOW,
    ASK,
    BOSS_LEVELS,
    DENY,
    AgentGrantStore,
    Authorizer,
    BossGrantStore,
    HoldQueue,
)
from core.pes.capability_registry import CapabilityRegistry


def _az(pes_dir):
    reg = CapabilityRegistry(pes_dir / "caps.json")
    reg.ensure_seeded()
    return Authorizer(
        registry=reg,
        boss=BossGrantStore(pes_dir / "boss.json"),
        agent=AgentGrantStore(pes_dir / "agent.json"),
        holds=HoldQueue(pes_dir / "holds.json"),
    )


# ---------------------------------------------------------------- 老板级
def test_老板级默认档是标准(pes_dir):
    assert BossGrantStore(pes_dir / "boss.json").get() == "标准"


def test_老板级三档可选(pes_dir):
    b = BossGrantStore(pes_dir / "boss.json")
    assert BOSS_LEVELS == ("只读", "标准", "高(需确认)")
    assert b.set("只读")["ok"] is True
    assert b.get() == "只读"


def test_老板级非法档被拒(pes_dir):
    assert BossGrantStore(pes_dir / "boss.json").set("随便")["ok"] is False


# ---------------------------------------------------------------- 撤销优先
def test_撤销优先于授权(pes_dir):
    a = AgentGrantStore(pes_dir / "agent.json")
    a.grant("write_file")
    assert a.is_granted("write_file") is True
    a.revoke("write_file", reason="老板撤回")
    assert a.is_granted("write_file") is False
    assert a.is_denied("write_file")["reason"] == "老板撤回"


def test_撤销后再授权才解除持续拒绝(pes_dir):
    a = AgentGrantStore(pes_dir / "agent.json")
    a.revoke("write_file")
    a.grant("write_file")
    assert a.is_granted("write_file") is True


# ---------------------------------------------------------------- 单一裁决
def test_未注册能力一律拒绝(pes_dir):
    d = _az(pes_dir).decide("nope")
    assert d["decision"] == DENY and d["reason"] == "unregistered_capability"


def test_只读能力放行(pes_dir):
    d = _az(pes_dir).decide("read_file")
    assert d["decision"] == ALLOW


def test_不可逆动作需逐次确认并带撤销窗口(pes_dir):
    d = _az(pes_dir).decide("publish")
    assert d["decision"] == ASK
    assert d["reversible_window_s"] == 900
    assert "撤回" in d["visibility_hint"]


def test_对外动作窗口是_120_秒(pes_dir):
    assert _az(pes_dir).decide("send_message")["reversible_window_s"] == 120


def test_老板级只读时只允许_R0(pes_dir):
    d = _az(pes_dir).decide("write_file", boss_level="只读")
    assert d["decision"] == DENY and d["reason"] == "boss_readonly"


def test_本地写无授权时需确认而非放行(pes_dir):
    d = _az(pes_dir).decide("write_file")
    assert d["decision"] == ASK and d["reason"] == "local_write_needs_grant"


def test_本地写有授权后放行(pes_dir):
    az = _az(pes_dir)
    az.agent.grant("write_file")
    d = az.decide("write_file")
    assert d["decision"] == ALLOW and d["reason"] == "local_write_granted"


def test_撤销态能力即便有授权也拒绝(pes_dir):
    az = _az(pes_dir)
    az.agent.grant("write_file")
    az.agent.revoke("write_file")
    d = az.decide("write_file")
    assert d["decision"] == DENY and d["reason"] == "revoked"


def test_裁决必带风险等级与是否需审批(pes_dir):
    d = _az(pes_dir).decide("publish")
    assert d["risk_level"] == "R3" and d["requires_approval"] is True


# ---------------------------------------------------------------- 可解释拒绝（对治假拒绝）
def test_每次拒绝都给为什么和怎么办(pes_dir):
    d = _az(pes_dir).explain("nope")
    assert d["decision"] == DENY
    assert d["why"] and d["how_to_fix"]


def test_只读档拒绝时给出调档办法(pes_dir):
    from core.pes.authorization import _how_to_fix

    d = _az(pes_dir).decide("write_file", boss_level="只读")
    assert "只读" in _how_to_fix(d)


def test_放行时无需操作(pes_dir):
    d = _az(pes_dir).explain("read_file")
    assert d["how_to_fix"] == "无需操作。"


# ---------------------------------------------------------------- 撤销窗口
def test_撤销窗口对用户可见(pes_dir):
    h = HoldQueue(pes_dir / "holds.json")
    h.hold("a1", "publish", 120)
    v = h.visibility("a1")
    assert v["show"] is True
    assert v["seconds_left"] > 100
    assert "撤回" in v["message"]


def test_窗口内可撤销_撤销后不再可见(pes_dir):
    h = HoldQueue(pes_dir / "holds.json")
    h.hold("a1", "publish", 120)
    assert h.revoke("a1") is True
    assert h.visibility("a1")["message"] == ""


def test_窗口_0_秒立即可放行(pes_dir):
    h = HoldQueue(pes_dir / "holds.json")
    h.hold("a1", "send_message", 0)
    assert [r["action_id"] for r in h.due()] == ["a1"]
    assert h.release("a1") is True
    assert h.due() == []


def test_未进窗的动作不可见(pes_dir):
    assert HoldQueue(pes_dir / "holds.json").visibility("nope") == {"show": False}


def test_撤销窗口队列本身也走状态唯一出口(pes_dir):
    from core.pes.state_integrity import detect_uninstrumented

    h = HoldQueue(pes_dir / "holds.json")
    h.hold("a1", "publish", 5)
    assert detect_uninstrumented(pes_dir / "holds.json")["instrumented"] is True
