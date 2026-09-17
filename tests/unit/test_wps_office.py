# -*- coding: utf-8 -*-
"""2026-09-09 wps_office 骨架: 注册/provider 策略/降级生成"""
import sys

sys.path.insert(0, ".")
import pytest

from core.gateway.tool_router import _TOOL_REGISTRY


def test_registered():
    assert "wps_office" in _TOOL_REGISTRY


def test_mcp_without_env_refuses():
    import os
    import tempfile

    from core.tools.wps_office import execute_wps_office

    md = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    md.write("## P1 标题\n- 要点1")
    md.close()
    r = execute_wps_office("pptx_from_md", md.name, provider="mcp")
    os.unlink(md.name)
    assert r.get("success") is False and "WPS 环境" in r.get("error", "")


def test_pptx_fallback(tmp_path):
    from core.tools.wps_office import execute_wps_office

    md = tmp_path / "x.md"
    md.write_text("## P1 封面\n- 卖点1\n## P2 正文\n- 数据2", encoding="utf-8")
    out = tmp_path / "x.pptx"
    r = execute_wps_office("pptx_from_md", str(md), out_path=str(out), provider="pptx")
    assert r.get("success") and r.get("provider") == "python-pptx" and out.exists()
