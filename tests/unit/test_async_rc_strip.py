# -*- coding: utf-8 -*-
"""2026-09-06: async(execute_agent_task)路径 reasoning_content 400 修复防回归。"""
import io

_ET = io.open("core/gateway/execute_agent_task.py", encoding="utf-8").read()


def test_async_entry_rc_strip():
    assert "[RC_STRIP] async 入口剥离" in _ET


def test_async_derive_last_task_only():
    assert "derive_messages(last_task_only=True)" in _ET


def test_async_final_rc_strip():
    assert "[RC_FINAL] 发送前剥离" in _ET
    assert "tool_calls" in _ET
