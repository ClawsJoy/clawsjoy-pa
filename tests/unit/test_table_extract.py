# -*- coding: utf-8 -*-
"""2026-09-07: table_extract 确定性工具 — 网页表格→MD 一次调用, 不让 LLM loop。"""
import sys

sys.path.insert(0, ".")
import pytest


def test_schema_registered_in_agent_tools():
    from core.lib.gateway_helpers import _get_agent_tools

    tools = _get_agent_tools()
    names = {t.get("function", {}).get("name") for t in tools if t}
    assert "table_extract" in names


def test_plugin_registered():
    from core.gateway.tool_router import _TOOL_REGISTRY

    assert "table_extract" in _TOOL_REGISTRY


def test_rows_to_md():
    from core.tools.table_extract import _rows_to_md

    md = _rows_to_md([["档位", "单价"], ["1", "5元"], ["2", "6元"]])
    assert md.startswith("| 档位 | 单价 |")
    assert "---" in md
    assert "6元" in md


def test_html_to_md_pandas():
    from core.tools.table_extract import _html_to_md

    html = "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
    md = _html_to_md(html, [["A", "B"], ["1", "2"]])
    assert "|" in md and "A" in md


def test_sheet_json_to_md():
    from core.tools.table_extract import _sheet_json_to_md

    # 模拟飞书 sheet 单元格 JSON: values 数组的数组, 单元格 {text:...}
    payload = {"data": {"values": [[{"text": "档位"}, {"text": "单价"}], [{"text": "1-5单"}, {"text": "5元"}]]}}
    import json

    md = _sheet_json_to_md(json.dumps(payload))
    assert md is not None
    assert "档位" in md and "5元" in md


def test_grid_text_to_md():
    from core.tools.table_extract import _grid_text_to_md

    md = _grid_text_to_md("档位  单价\nA档  5元\nB档  6元")
    assert md and "A档" in md


def test_private_host_blocked():
    from core.tools.table_extract import extract_tables

    r = extract_tables("http://127.0.0.1/x", user_id="u1")
    assert r.get("success") is False
    assert "内网" in r.get("error", "") or "仅支持" in r.get("error", "")
