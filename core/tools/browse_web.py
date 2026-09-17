"""browse_web 工具插件 — 只读网页浏览(包装已有 handler)

直接转发 core/lib/gateway_helpers._handle_browse_web(WebCache.query:
缓存 → SAG → 抓取, 返回标题/关键文本/路由/API 路径, 1万字符截断)。
不修改 handler 内部逻辑, 仅包装为 ToolPlugin 形态接入 _TOOL_REGISTRY。
"""
from core.tools.base import ToolPlugin
from core.lib.gateway_helpers import _handle_browse_web, _get_default_tools

BROWSE_WEB_SCHEMA = next(
    (t for t in _get_default_tools() if t.get("function", {}).get("name") == "browse_web"),
    None,
)


class BrowseWebPlugin(ToolPlugin):
    name = "browse_web"
    quota = 10
    schema = BROWSE_WEB_SCHEMA

    def execute(self, args: dict, ctx) -> dict:
        return _handle_browse_web(args or {})
