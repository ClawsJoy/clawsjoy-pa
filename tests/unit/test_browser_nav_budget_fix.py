# -*- coding: utf-8 -*-
"""2026-09-07: 长文档调研烧穿预算的两个收敛修复
1) browser_local 同 URL navigate 熔断(3 分钟窗 ≥3 次拒绝)
2) 预算水位截断 → 无工具收尾轮(模型真实总结, 不再空模板)"""
import sys

sys.path.insert(0, ".")
import pytest

from core.tools.browser_local import _NAV_HIST, _navigate_over_limit


@pytest.fixture(autouse=True)
def _clear():
    _NAV_HIST.clear()
    yield
    _NAV_HIST.clear()


def test_same_url_nav_limit():
    """同一 URL navigate 3 次内放行, ≥3 次拒绝"""
    assert _navigate_over_limit("u1", "https://a.com/x") == ""
    assert _navigate_over_limit("u1", "https://a.com/x") == ""
    msg = _navigate_over_limit("u1", "https://a.com/x")
    assert msg and "停止重复导航" in msg


def test_diff_url_independent():
    """不同 URL 各自计数"""
    for _ in range(4):
        _navigate_over_limit("u1", "https://a.com/1")
    assert _navigate_over_limit("u1", "https://a.com/2") == ""
    assert _navigate_over_limit("u1", "https://a.com/2") == ""


def test_user_isolated():
    """不同 user 不串扰"""
    for _ in range(3):
        _navigate_over_limit("uA", "https://x.com/p")
    assert _navigate_over_limit("uB", "https://x.com/p") == ""


def test_plugin_wires_guard():
    """execute 里 navigate 接入了熔断"""
    src = open("core/tools/browser_local.py", encoding="utf-8").read()
    assert 'action == "navigate" and url' in src
    assert "_navigate_over_limit(user_id, url)" in src
    assert "guard_denied" in src


def test_budget_stop_has_final_round():
    """预算截断: 系统指令 + 无工具收尾轮, 而非伪造空模板"""
    src = open("core/gateway/v9_bridge/response_guard.py", encoding="utf-8").read()
    assert "无工具收尾总结" in src
    assert "tools=[]" in src
    assert "回复「继续」" in src
    assert "禁止再调用任何工具" in src
