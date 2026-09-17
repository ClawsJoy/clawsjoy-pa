"""browser_local evaluate 修复测试: expr 字段递归 key + 写操作保护"""
import sys

sys.path.insert(0, ".")
import pytest


def test_evaluate_expr_field_in_recursive_key():
    """evaluate 用 expr 字段(非 expression) → 递归 key 含 expr 前50字符"""
    from core.gateway.path_utils import _extract_tool_path

    k1 = _extract_tool_path({"action": "evaluate", "expr": "document.querySelector('a').click()"}, "browser_local")
    k2 = _extract_tool_path({"action": "evaluate", "expr": "document.querySelector('b').click()"}, "browser_local")
    assert k1 != k2, "不同 expr 应不同 key"
    assert k1.startswith("browser_local:evaluate:") and "querySelector" in k1, k1


def test_extract_expr_field_in_recursive_key():
    """extract 用 expr 字段 → 递归 key 含 expr"""
    from core.gateway.path_utils import _extract_tool_path

    k1 = _extract_tool_path({"action": "extract", "expr": "document.body.innerText"}, "browser_local")
    k2 = _extract_tool_path({"action": "extract", "expr": "document.title"}, "browser_local")
    assert k1 != k2, "不同 extract expr 应不同 key"
    assert "innerText" in k1


def test_evaluate_write_guard_in_tool_source():
    """evaluate 写保护: 源码含 click/submit 标记检测"""
    _SRC = open("core/tools/browser_local.py", encoding="utf-8").read()
    assert "evaluate 是只读探测通道" in _SRC, "应有写保护提示"
    assert '".click("' in _SRC or ".click(" in _SRC, "应检测 click 写操作"
    assert '".submit("' in _SRC, "应检测 submit 写操作"
