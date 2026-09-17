# -*- coding: utf-8 -*-
"""2026-09-06 修复3 防回归: 写类任务只读侦察死循环 → ≥5轮无写入注入收敛提醒。
Agent 曾侦察 47 步(obsidian_knowledge/read_file)从不 write_draft, 直到空回复收场, 纯烧 token。"""
import io

_GW = io.open("core/gateway/v9_bridge/llm_call.py", encoding="utf-8").read()


def test_readonly_loop_converge_present():
    """应存在 READONLY_LOOP 收敛注入逻辑"""
    assert "[READONLY_LOOP]" in _GW
    assert "仍在侦察" in _GW
    assert "停止继续读取资料" in _GW


def test_trigger_conditions():
    """触发: 用户要求写 + tracker 无写入 + round>=5"""
    assert "_any_user_wants_write" in _GW
    assert "_wrote5" in _GW
    assert "_loop_readonly_rounds >= 5" in _GW


def test_injection_guides_write_draft():
    """收敛提醒应明确指导 write_draft 调用方式(抖音草稿)"""
    i = _GW.find("_steer5 = (")
    seg = _GW[i : i + 600]
    assert "write_draft" in seg
    assert "platform=抖音" in seg
    assert "回读验证" in seg
