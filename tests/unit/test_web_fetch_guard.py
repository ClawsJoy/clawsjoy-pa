"""WebFetchGuard 单测: 同一 URL 累计 ≤3 次, 超出 deny; 第 2 次起 warn"""
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _reset_tracker(monkeypatch):
    import core.gateway.execute_agent_task as eat

    monkeypatch.setattr(eat, "_recursion_tracker", {})
    yield


def _payload(url, tool="fetch_web", session="s1"):
    return {"tool": tool, "args": {"url": url}, "session_id": session, "task_id": "t1"}


def test_first_call_passes():
    from core.gateway.guards.registry import WebFetchGuard

    g = WebFetchGuard()
    assert g.check(_payload("https://a.com/x")) is None


def test_same_url_threshold_denies_on_4th():
    from core.gateway.guards.registry import WebFetchGuard

    g = WebFetchGuard()
    for i in range(1, 4):
        assert g.check(_payload("https://a.com/x")) is None, f"第 {i} 次应放行"
    denied = g.check(_payload("https://a.com/x"))
    assert denied is not None
    assert denied.get("status") == "paused"
    assert "3" in denied.get("reason", "")


def test_warn_on_second_call():
    from core.gateway.guards.registry import WebFetchGuard

    g = WebFetchGuard()
    p1 = _payload("https://a.com/y")
    g.check(p1)
    p2 = _payload("https://a.com/y")
    assert g.check(p2) is None  # 放行
    assert p2.get("guard_results", {}).get("web_fetch_warn")


def test_different_urls_not_counted():
    from core.gateway.guards.registry import WebFetchGuard

    g = WebFetchGuard()
    for url in ("https://a.com/1", "https://a.com/2", "https://a.com/3", "https://a.com/4"):
        assert g.check(_payload(url)) is None


def test_different_urls_then_same_url():
    """不同 URL 各自计数(不因 <no-path> 误伤); 同一 URL 第 4 次才拒绝"""
    from core.gateway.guards.registry import WebFetchGuard

    g = WebFetchGuard()
    # 4 个不同 URL 各 1 次 → 全部放行
    for url in ("https://a.com/1", "https://a.com/2", "https://a.com/3", "https://a.com/4"):
        assert g.check(_payload(url)) is None, url
    # 同一 URL 累计 4 次 → 第 4 次拒绝
    for i in range(1, 4):
        assert g.check(_payload("https://a.com/x")) is None, f"第 {i} 次应放行"
    denied = g.check(_payload("https://a.com/x"))
    assert denied is not None and denied.get("status") == "paused"


def test_playwright_browser_included():
    """playwright_browser 也走 URL 递归计数(不同 URL 不共计数)"""
    from core.gateway.guards.registry import WebFetchGuard

    g = WebFetchGuard()
    for url in ("https://a.com/p1", "https://a.com/p2"):
        assert g.check(_payload(url, tool="playwright_browser")) is None, url
    # 同 URL 第 4 次拒绝
    for i in range(1, 4):
        assert g.check(_payload("https://a.com/zz", tool="playwright_browser")) is None
    denied = g.check(_payload("https://a.com/zz", tool="playwright_browser"))
    assert denied is not None and denied.get("status") == "paused"


def test_url_missing_fallback_to_tool():
    """URL 缺失时 fallback 工具名计数(不崩)"""
    from core.gateway.guards.registry import WebFetchGuard

    g = WebFetchGuard()
    p = {"tool": "fetch_web", "args": {}, "session_id": "s1", "task_id": "t1"}
    assert g.check(p) is None  # 无 url 无 task? 有 task_id → 按 <no-url>:fetch_web 计数
    assert g.check(p) is None
    assert g.check(p) is None
    denied = g.check(p)
    assert denied is not None and denied.get("status") == "paused"


def test_extract_tool_path_uses_url():
    """_extract_tool_path 对网络工具提取 URL 作为递归 key(避免 <no-path> 误伤)"""
    from core.gateway.path_utils import _extract_tool_path

    assert _extract_tool_path({"url": "https://a.com/1"}) == "https://a.com/1"
    assert _extract_tool_path({"url": "https://a.com/1"}) == _extract_tool_path({"url": "https://a.com/1"})
    assert _extract_tool_path({"url": "https://a.com/1"}) != _extract_tool_path({"url": "https://a.com/2"})
    assert _extract_tool_path({"action": "open", "url": "https://b.com"}) == "https://b.com"
    # 非网络工具不受影响
    assert _extract_tool_path({"path": "/x"}) == "/x"
    assert _extract_tool_path({}) == "<no-path>"


def test_non_web_tool_unaffected():
    from core.gateway.guards.registry import WebFetchGuard

    g = WebFetchGuard()
    assert g.check({"tool": "read_file", "args": {"path": "/x"}, "session_id": "s1", "task_id": "t1"}) is None
    assert g.check({"tool": "browse_web", "args": {}, "session_id": "s1", "task_id": "t1"}) is None  # 无 url


def test_registered_in_guard_order():
    from core.gateway.guards.registry import guard_names

    names = guard_names()
    assert "web_fetch_guard" in names
    assert names.index("web_fetch_guard") > names.index("recursion_guard")
