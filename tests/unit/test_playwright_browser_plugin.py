"""playwright_browser 插件单测: 包装类转发 + SSRF(SSRF 校验先于 playwright import)"""
import sys

sys.path.insert(0, ".")
import pytest


def test_playwright_browser_forwards_to_handler(monkeypatch):
    import core.tools.playwright_browser as pb  # 插件模块级引用, patch 这里
    from core.tools.playwright_browser import PlaywrightBrowserPlugin

    captured = {}

    def _fake_handler(params):
        captured["params"] = params
        return {"success": True, "action": params.get("action"), "url": params.get("url")}

    monkeypatch.setattr(pb, "_handle_playwright_browser", _fake_handler)
    plugin = PlaywrightBrowserPlugin()
    assert plugin.name == "playwright_browser"
    r = plugin.execute({"action": "open", "url": "https://example.com"}, object())
    assert r["success"] and captured["params"]["action"] == "open"
    assert r["url"] == "https://example.com"


def test_playwright_browser_schema_present():
    from core.tools.playwright_browser import PlaywrightBrowserPlugin

    assert PlaywrightBrowserPlugin.schema is not None
    assert PlaywrightBrowserPlugin.schema["function"]["name"] == "playwright_browser"
    props = PlaywrightBrowserPlugin.schema["function"]["parameters"]["properties"]
    assert props["action"]["enum"] == ["open", "content", "click", "fill", "screenshot"]


def test_playwright_browser_ssrf_private_blocked():
    """SSRF 守卫在 playwright import 之前: 内网 URL 直接拒绝(不依赖 playwright 安装)。"""
    from core.lib.gateway_helpers import _handle_playwright_browser

    r = _handle_playwright_browser({"action": "open", "url": "http://127.0.0.1:8080/admin"})
    assert not r["success"] and "内网" in r["error"], r


def test_playwright_browser_sets_browsers_path_default():
    """handler 应默认设置 PLAYWRIGHT_BROWSERS_PATH(部署 chromium 缓存, 可被 env 覆盖)"""
    src = open("core/lib/gateway_helpers.py", encoding="utf-8").read()
    seg = src[
        src.index("def _handle_playwright_browser") : src.index("def _handle_browse_web")
        if "def _handle_browse_web" in src[src.index("def _handle_playwright_browser") :]
        else len(src)
    ]
    assert 'os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH"' in seg, "应 setdefault chromium 缓存路径"


def test_playwright_browser_registered():
    from core.gateway.tool_router import _TOOL_REGISTRY

    assert "playwright_browser" in _TOOL_REGISTRY


def test_playwright_schema_mentions_spa():
    """playwright schema 描述应标注 SPA 适配; fetch_web 应标注仅服务端渲染"""
    from core.tools.fetch_web import FetchWebPlugin
    from core.tools.playwright_browser import PlaywrightBrowserPlugin

    assert "SPA" in PlaywrightBrowserPlugin.schema["function"]["description"]
    assert "React" in PlaywrightBrowserPlugin.schema["function"]["description"]
    assert "SPA" in FetchWebPlugin.schema["function"]["description"]
    assert "服务端渲染" in FetchWebPlugin.schema["function"]["description"]


def test_playwright_handler_goto_wait_load_and_retry():
    """handler: goto 用 load(非 domcontentloaded) + content 空壳重试(等 JS 渲染)"""
    src = open("core/lib/gateway_helpers.py", encoding="utf-8").read()
    seg = src[
        src.index("def _handle_playwright_browser") : src.index("def _handle_web_search")
        if "def _handle_web_search" in src[src.index("def _handle_playwright_browser") :]
        else len(src)
    ]
    # goto 等待策略: load + 2s hydrate
    assert 'wait_until="load"' in seg, "goto 应等待 load(而非 domcontentloaded)"
    assert "wait_for_timeout(2000)" in seg, "goto 后应等待 JS 渲染"
    # content 空壳重试: 过短(<60)时循环重试
    assert "while len(text_content) < 60" in seg, "空壳防护: inner_text 过短应重试"
    assert "wait_extra_s" in seg and '"note"' in seg, "应返回等待时长提示"
