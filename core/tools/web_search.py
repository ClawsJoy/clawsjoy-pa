"""web_search 工具插件 — 搜索引擎查询(只读)

2026-08-30 新增: 解决 Google News 混淆 URL 死胡同 — Agent 拿到 news.google.com/articles/CBM...
无法 fetch 原文(400/跨源), 用标题搜索原文来源站即可。转发 _handle_web_search(Bing HTML 解析)。
"""
from core.tools.base import ToolPlugin
from core.lib.gateway_helpers import _handle_web_search, _get_default_tools

WEB_SEARCH_SCHEMA = next(
    (t for t in _get_default_tools() if t.get("function", {}).get("name") == "web_search"),
    None,
)


class WebSearchPlugin(ToolPlugin):
    name = "web_search"
    quota = 10
    schema = WEB_SEARCH_SCHEMA

    def execute(self, args: dict, ctx) -> dict:
        return _handle_web_search(args or {})
