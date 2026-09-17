"""obsidian_knowledge 工具插件 — S4 单轨分发(原 tool_router elif 迁至 handler)。

execute → core.lib.gateway_helpers._handle_obsidian_knowledge(params, user_id, session_id)。
"""
from core.tools.base import ToolPlugin
from core.lib.gateway_helpers import _handle_obsidian_knowledge, _get_default_tools

OBSIDIAN_SCHEMA = next(
    (t for t in _get_default_tools() if t.get("function", {}).get("name") == "obsidian_knowledge"),
    None,
)


class ObsidianKnowledgePlugin(ToolPlugin):
    name = "obsidian_knowledge"
    quota = 20
    schema = OBSIDIAN_SCHEMA

    def execute(self, args: dict, ctx) -> dict:
        return _handle_obsidian_knowledge(
            args or {},
            user_id=str(getattr(ctx, "user_id", "") or ""),
            session_id=str(getattr(ctx, "session_id", "") or ""),
        )
