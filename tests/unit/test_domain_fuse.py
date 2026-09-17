# -*- coding: utf-8 -*-
"""2026-09-09: 同域熔断 — 网络工具失败 ≥2 换源 / ≥3 停域"""
import sys

sys.path.insert(0, ".")
import pytest


def test_domain_fuse_in_bridge():
    src = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "DOMFAIL_STOP" in src and "DOMFAIL_HARD" in src
    assert '_df_tools = ("fetch_web", "browse_web", "browser_local"' in src
    assert "停止重试该域" in src and "待线下核实" in src
    assert "add_steer as _st_df" in src
