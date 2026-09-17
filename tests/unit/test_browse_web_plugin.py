"""browse_web 插件单测: 包装类正确转发已有 handler, 不改内部逻辑"""
import sys

sys.path.insert(0, ".")
import pytest


def test_browse_web_forwards_to_handler(monkeypatch):
    import core.tools.browse_web as bw  # 插件模块级引用, patch 这里
    from core.tools.browse_web import BrowseWebPlugin

    captured = {}

    def _fake_handler(params):
        captured["params"] = params
        return {"success": True, "source": "mock", "url": params.get("url"), "content": "mock content"}

    monkeypatch.setattr(bw, "_handle_browse_web", _fake_handler)
    plugin = BrowseWebPlugin()
    assert plugin.name == "browse_web"
    r = plugin.execute({"url": "https://example.com"}, object())
    assert r["success"] and captured["params"] == {"url": "https://example.com"}
    assert r["url"] == "https://example.com"


def test_browse_web_returns_pure_text(monkeypatch):
    """browse_web 返回纯文本: 缓存/SAG 给原始 HTML 时也要去标签(幂等)"""
    import core.lib.web_cache as wc
    import core.tools.browse_web as bw
    from core.tools.browse_web import BrowseWebPlugin

    raw_html = "<html><head><title>News</title></head><body><h1>Title</h1><script>alert(1)</script><p>正文 &amp; 内容</p></body></html>"
    monkeypatch.setattr(
        wc,
        "WebCache",
        lambda *a, **k: type(
            "C",
            (),
            {
                "query": lambda self, url: {
                    "source": "fetch",
                    "metadata": {"key_text": raw_html, "title": "News", "routes": [], "api_paths": []},
                }
            },
        )(),
    )
    r = BrowseWebPlugin().execute({"url": "https://example.com"}, object())
    assert r["success"], r
    assert "<h1>" not in r["content"] and "<script>" not in r["content"]
    assert "alert" not in r["content"]
    assert "正文 & 内容" in r["content"]  # 实体已反转义
    assert "Title" in r["content"]


def test_browse_web_schema_present():
    from core.tools.browse_web import BrowseWebPlugin

    assert BrowseWebPlugin.schema is not None
    assert BrowseWebPlugin.schema["function"]["name"] == "browse_web"
    assert "url" in BrowseWebPlugin.schema["function"]["parameters"]["properties"]


def test_browse_web_registered():
    from core.gateway.tool_router import _TOOL_REGISTRY

    assert "browse_web" in _TOOL_REGISTRY
