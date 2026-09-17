"""browser_hybrid 工具插件 — Computer Use 混合方案(包装已有 handler)

设计: docs/reports/computer_use_agent_design_20260904.md §1
enumerate(枚举可交互元素) → Agent/LLM 选序号 → click/fill/type/press/select_option/hover
(按 DOM 选择器执行+验证) / observe(断言) / close(释放)。坐标从不作点击依据。
页面状态按 page_id 保留; 截图强制落沙箱 data/screenshots/。
"""
from core.tools.base import ToolPlugin
from core.lib.gateway_helpers import _handle_browser_hybrid, _get_default_tools

BROWSER_HYBRID_SCHEMA = next(
    (t for t in _get_default_tools() if t.get("function", {}).get("name") == "browser_hybrid"),
    None,
)


class BrowserHybridPlugin(ToolPlugin):
    name = "browser_hybrid"
    quota = 20
    schema = BROWSER_HYBRID_SCHEMA

    def execute(self, args: dict, ctx) -> dict:
        """执行; screenshot action 强制落沙箱 data/screenshots/ 并挂截图字段。"""
        import os as _os
        args = dict(args or {})
        action = (args.get("action") or "").strip()
        base = getattr(ctx, "base", None)
        if action in ("screenshot", "click", "fill", "type", "press", "select_option", "hover", "enumerate", "observe") and base is not None:
            _sb = str(base)
            _shot_dir = _os.path.join(_sb, "data", "screenshots")
            _os.makedirs(_shot_dir, exist_ok=True)
            if args.get("screenshot_path"):
                args["screenshot_path"] = _os.path.join(_shot_dir, _os.path.basename(args["screenshot_path"]))
        result = _handle_browser_hybrid(args or {})
        if result.get("success") and base is not None:
            # 截图字段挂前端缩略图(若返回证据/路径)
            for key in ("screenshot_path", "evidence"):
                p = None
                if key == "screenshot_path":
                    p = result.get("screenshot_path")
                elif isinstance(result.get("evidence"), dict):
                    p = result["evidence"].get("screenshot_path")
                if p:
                    try:
                        rel = _os.path.relpath(str(p), str(base))
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
