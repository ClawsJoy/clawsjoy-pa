# -*- coding: utf-8 -*-
"""2026-09-09 wps_office 骨架: 注册/provider 策略/降级生成"""
import sys
from pathlib import Path

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


# ---------- 2026-09-18 alpha: out_path must share the root with md_path ----------


def _sb(tmp_path):
    sb = tmp_path / "data" / "projects" / "u1" / "s1" / "clawsjoy_dev"
    (sb / "data" / "reports").mkdir(parents=True)
    return sb


def test_out_path_default_anchored_to_base(tmp_path):
    from core.tools.wps_office import execute_wps_office as ex

    sb = _sb(tmp_path)
    (sb / "data/reports/x.md").write_text("## P1 cover\n- point 1", encoding="utf-8")
    r = ex("pptx_from_md", "data/reports/x.md", provider="pptx", base=str(sb))
    assert r.get("success") is True, r
    got = str(r.get("out_path") or "").replace("\\", "/")
    assert got.startswith(str(sb).replace("\\", "/")), "out_path not anchored to base: %r" % got
    assert got.endswith("data/reports/x.pptx"), got
    assert (sb / "data/reports/x.pptx").exists()


def test_out_path_explicit_relative_anchored_to_base(tmp_path):
    from core.tools.wps_office import execute_wps_office as ex

    sb = _sb(tmp_path)
    (sb / "data/reports/x.md").write_text("## P1 cover\n- point 1", encoding="utf-8")
    r = ex(
        "pptx_from_md",
        "data/reports/x.md",
        provider="pptx",
        out_path="data/reports/renamed.pptx",
        base=str(sb),
    )
    assert r.get("success") is True, r
    assert (sb / "data/reports/renamed.pptx").exists()


def test_out_path_clawsjoy_dev_prefix_not_doubled(tmp_path):
    from core.tools.wps_office import execute_wps_office as ex

    sb = _sb(tmp_path)
    (sb / "data/reports/x.md").write_text("## P1 cover\n- point 1", encoding="utf-8")
    r = ex(
        "pptx_from_md",
        "data/reports/x.md",
        provider="pptx",
        out_path="clawsjoy_dev/data/reports/z.pptx",
        base=str(sb),
    )
    assert r.get("success") is True, r
    got = str(r.get("out_path") or "").replace("\\", "/")
    assert "clawsjoy_dev/clawsjoy_dev" not in got, got
    assert (sb / "data/reports/z.pptx").exists()


def test_out_path_absolute_untouched(tmp_path):
    from core.tools.wps_office import execute_wps_office as ex

    sb = _sb(tmp_path)
    (sb / "data/reports/x.md").write_text("## P1 cover\n- point 1", encoding="utf-8")
    dst = tmp_path / "elsewhere" / "abs.pptx"
    dst.parent.mkdir(parents=True)
    r = ex("pptx_from_md", "data/reports/x.md", provider="pptx", out_path=str(dst), base=str(sb))
    assert r.get("success") is True, r
    assert dst.exists()


def test_resolve_out_path_table():
    from core.tools.wps_office import _resolve_out_path as f

    assert f("", "pptx_from_md", "a/b/x.md", "") == "data/reports/x.pptx"
    assert f("", "pptx_from_md", "a/b/x.md", "SB") == str(Path("SB") / "data/reports/x.pptx")
    assert f("data/reports/y.pptx", "pptx_from_md", "a/b/x.md", "SB") == str(Path("SB") / "data/reports/y.pptx")
    assert f("clawsjoy_dev/data/reports/y.pptx", "pptx_from_md", "a/b/x.md", "SB") == str(
        Path("SB") / "data/reports/y.pptx"
    )
    assert f("data\\reports\\y.pptx", "pptx_from_md", "a/b/x.md", "SB") == str(
        Path("SB") / "data/reports/y.pptx"
    )
    assert f("/abs/y.pptx", "pptx_from_md", "a/b/x.md", "SB") == "/abs/y.pptx"
    assert f("D:/abs/y.pptx", "pptx_from_md", "a/b/x.md", "SB") == "D:/abs/y.pptx"


def test_execute_wps_office_path_is_resolved_by_helper():
    import ast

    src = Path("core/tools/wps_office.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "execute_wps_office"]
    assert len(fn) == 1
    called = {n.func.id for n in ast.walk(fn[0]) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "_resolve_out_path" in called, sorted(called)
    assert any(isinstance(n, ast.FunctionDef) and n.name == "_resolve_out_path" for n in tree.body)
