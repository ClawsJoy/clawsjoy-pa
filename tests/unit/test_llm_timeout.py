# -*- coding: utf-8 -*-
"""DeepSeek adapter 超时回归: execute/execute_json 保持 180s(2026-08-26 长上下文修复)"""
import sys

sys.path.insert(0, ".")
import pytest

_SRC = open("core/lib/v8/adapters/deepseek_adapter.py", encoding="utf-8").read()


def test_deepseek_execute_timeout_180s():
    """execute/execute_json 应为 timeout=180(长上下文 Read timed out 修复)"""
    assert _SRC.count("timeout=180") >= 2, "execute/execute_json 应保持 timeout=180"
