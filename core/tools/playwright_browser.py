"""playwright_browser 工具插件 — 浏览器自动化(包装已有 handler)

直接转发 core/lib/gateway_helpers._handle_playwright_browser(
open/content/click/fill/screenshot 5 个 action; SSRF 守卫 _is_private_host 已接;
goto 30s / click 10s 超时; finally browser.close() 释放)。
不修改 handler 内部逻辑, 仅包装为 ToolPlugin 形态接入 _TOOL_REGISTRY。
"""
from core.tools.base import ToolPlugin
from core.lib.gateway_helpers import _handle_playwright_browser, _get_default_tools

PLAYWRIGHT_BROWSER_SCHEMA = next(
    (t for t in _get_default_tools() if t.get("function", {}).get("name") == "playwright_browser"),
    None,
)


class PlaywrightBrowserPlugin(ToolPlugin):
    name = "playwright_browser"
    quota = 10
    schema = PLAYWRIGHT_BROWSER_SCHEMA

    def execute(self, args: dict, ctx) -> dict:
        """执行浏览器操作; screenshot action 强制落沙箱 data/screenshots/ 并挂截图字段。

        截图流可视化: 成功截图后返回 screenshot_path(沙箱相对) + screenshot_url(/v9/media),
        tool_step 透传给前端渲染缩略图。截图不写网关 CWD/任意路径(沙箱隔离)。
        """
        import os as _os
        args = dict(args or {})
        action = (args.get("action") or "").strip()
        base = getattr(ctx, "base", None)
        if action == "screenshot" and base is not None:
            _sb = str(base)
            _shot_dir = _os.path.join(_sb, "data", "screenshots")
            _os.makedirs(_shot_dir, exist_ok=True)
            # 尊重 LLM 指定文件名, 但强制落入沙箱目录(防写沙箱外)
            _fname = _os.path.basename(args.get("screenshot_path") or "") or "playwright_%d.png" % _os.getpid()
            args["screenshot_path"] = _os.path.join(_shot_dir, _fname)
        result = _handle_playwright_browser(args or {})
        if result.get("success") and result.get("path") and base is not None:
            try:
                rel = _os.path.relpath(result["path"], str(base))
                if not rel.startswith(".."):
                    rel = rel.replace("\\", "/")
                    result["screenshot_path"] = rel
                    result["screenshot_url"] = (
                        "/v9/media?user_id=%s&session_id=%s&path=%s"
                        % (getattr(ctx, "user_id", "") or "", getattr(ctx, "session_id", "") or "", rel)
                    )
            except Exception:
                pass
        return result
