# -*- coding: utf-8 -*-
"""2026-09-06: tool_calls assistant 必须带 reasoning_content 键(值可空串) — 防 DeepSeek 400。
根因: if truthy 才加 RC, round 返回 reasoning 空/None 时键缺失, derive 异常回退内存直发 → 400。"""
import io

_ET = io.open("core/gateway/execute_agent_task.py", encoding="utf-8").read()
_GW = io.open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()


def test_exec_task_rc_key_always():
    """execute_agent_task: tool_calls assistant 无条件带 reasoning_content 键"""
    assert '_assistant_msg["reasoning_content"] = msg.get("reasoning_content")' in _ET


def test_bridge_rc_key_always():
    """同步 bridge: tool_calls assistant 无条件带 reasoning_content 键"""
    assert '_bassist["reasoning_content"] = bmsg.get("reasoning_content")' in _GW


def test_no_conditional_rc_add():
    """两处都不应再有 if truthy 才加 RC 的旧写法"""
    i = _ET.find('_assistant_msg["reasoning_content"]')
    assert "if msg.get" not in _ET[max(0, i - 100) : i]
    j = _GW.find('_bassist["reasoning_content"]')
    assert "if _bmsg.get" not in _GW[max(0, j - 100) : j]
