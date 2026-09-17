"""evaluate 递归计数修复测试: expression 前 50 字符作为递归 key"""
import sys

sys.path.insert(0, ".")
import pytest

from core.gateway.path_utils import _extract_tool_path


def test_evaluate_expression_distinct_key():
    """不同 expression 的 evaluate 应不同递归 key(不共用计数)"""
    k1 = _extract_tool_path({"action": "evaluate", "expression": "document.title"}, "browser_local")
    k2 = _extract_tool_path(
        {"action": "evaluate", "expression": "document.querySelectorAll('a').length"}, "browser_local"
    )
    assert k1 != k2, f"不同 expression 应不同 key: {k1} vs {k2}"
    assert k1.startswith("browser_local:evaluate:"), k1
    assert "document.title" in k1


def test_evaluate_same_expression_same_key():
    """相同 expression 的 evaluate 应相同 key(可递归检测)"""
    k1 = _extract_tool_path({"action": "evaluate", "expression": "document.title"}, "browser_local")
    k2 = _extract_tool_path({"action": "evaluate", "expression": "document.title"}, "browser_local")
    assert k1 == k2


def test_evaluate_expression_truncated_50():
    """expression 超 50 字符截断(长脚本不爆 key)"""
    long_expr = "x" * 200
    k = _extract_tool_path({"action": "evaluate", "expression": long_expr}, "browser_local")
    assert len(k) <= len("browser_local:evaluate:") + 50, f"key 应截断: {len(k)}"


def test_evaluate_no_expression_fallback():
    """evaluate 无 expression → 回退 browser_local:evaluate"""
    k = _extract_tool_path({"action": "evaluate"}, "browser_local")
    assert k == "browser_local:evaluate"


def test_browser_local_other_actions_unaffected():
    """其他 action(click/navigate) 行为不变(url/selector 优先)"""
    k = _extract_tool_path({"action": "click", "selector": "#btn"}, "browser_local")
    assert k == "browser_local:click:#btn"
    k2 = _extract_tool_path({"action": "navigate", "url": "https://x.com"}, "browser_local")
    assert k2 == "browser_local:navigate:https://x.com"
