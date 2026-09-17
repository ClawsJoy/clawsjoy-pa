# -*- coding: utf-8 -*-
"""2026-09-07: 工具空参校验与 schema 对齐 + 浏览器不可用熔断
根因1: fetch_web/browse_web schema/handler 只要求 url, 但 _EMPTY_REQUIRED 误标 action
       → 每次调用被拦「缺少 action」→ 模型反复空参重试烧步数。
根因2: browser_local 浏览器实例不可用仍反复重试 → 连续 2 次注入换路提示。"""
import sys

sys.path.insert(0, ".")
import pytest

from core.gateway.shared_state import browser_unavailable_error, empty_arg_error


def test_fetch_web_requires_url_not_action():
    """fetch_web: url 满足必填; 空调用报 url"""
    assert empty_arg_error("fetch_web", {"url": "https://a.com"}) == ""
    assert "url" in empty_arg_error("fetch_web", {})
    assert "action" not in empty_arg_error("fetch_web", {})
    assert empty_arg_error("fetch_web", {"action": "x"}) != "", "无 url 仍应拦截"


def test_browse_web_requires_url():
    assert empty_arg_error("browse_web", {"url": "https://a.com"}) == ""
    assert "url" in empty_arg_error("browse_web", {})


def test_action_tools_still_require_action():
    """真 action 类工具不受影响"""
    assert "action" in empty_arg_error("obsidian_knowledge", {})
    assert empty_arg_error("playwright_browser", {"url": "https://a.com"}) != ""
    assert empty_arg_error("browser_local", {}) != ""
    assert empty_arg_error("write_file", {}) != ""


def test_source_marked_url():
    src = open("core/gateway/shared_state.py", encoding="utf-8").read()
    assert '"browse_web": "url"' in src
    assert '"fetch_web": "url"' in src


def test_browser_unavailable_detected():
    """浏览器不可用标记命中"""
    assert browser_unavailable_error(
        {"success": False, "error": "浏览器不可用: BrowserContext.new_page: Target page, context or browser has been closed"}
    )
    assert browser_unavailable_error(
        {"success": False, "error": "{'error': 'Page.goto: Target page, context or browser has been closed'}"}
    )
    assert browser_unavailable_error({"success": True, "error": ""}) == ""
    assert browser_unavailable_error({"success": False, "error": "网络超时"}) == ""


def test_bridge_has_browser_circuit_breaker():
    """桥接含浏览器不可用熔断逻辑"""
    _TR = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "browser_unavailable_error" in _TR
    assert "_buv_cnt == 2" in _TR or "_buv_cnt >= 2" in _TR
    assert "BROWSER_UNAVAIL_STOP" in _TR
    assert "fetch_web/browse_web 需 url" in _TR or "fetch_web/browse_web 需 url" in _TR
