# -*- coding: utf-8 -*-
"""2026-09-08: write_file 空 path 引导增强 — 拦截消息带补参示例, 连续空参分级升级(2次格式引导/4次硬停)"""
import sys

sys.path.insert(0, ".")
import pytest


def test_bridge_missing_path_has_example():
    """空 path 拦截消息附具体补参示例"""
    src = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "补参示例: write_file(path" in src
    assert "缺少必填参数 path" in src
    assert "data/reports/" in src


def test_bridge_steer_tool_specific_at_2():
    """连续 2 次空参 → write_file 专属格式引导"""
    src = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "已连续 2 次以空参数调用 write_file" in src
    assert "先用 list_dir 确认目录" in src


def test_bridge_escalation_at_4():
    """连续 4 次空参 → 硬停提示(不再允许空参)"""
    src = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "已连续 4 次空参/缺参调用" in src
    assert "禁止再次空参调用" in src


def test_shared_helper_unchanged():
    """shared empty_arg_error 仍为原始语义(前缀不变)"""
    from core.gateway.shared_state import empty_arg_error as ea

    msg = ea("write_file", {})
    assert msg.startswith("write_file 缺少必填参数 path")
