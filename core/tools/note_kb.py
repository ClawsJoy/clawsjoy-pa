# -*- coding: utf-8 -*-
u"""note_kb 工具插件 —— note 内核之**六面之口**（承 pm_1442 §二.2 ／ pm_1444 §二.2 之准）。

【分界】**内核**（库根之解析 ／ 目录约定 ／ 最小 frontmatter）在 `core/lib/note_kernel.py`
  —— **⛔ 插件化**；本档唯**面 ／ 动作** ⇒ 走既有 `ToolPlugin` ＋ `_TOOL_REGISTRY`。
【六面】列 ／ 读 ／ 搜 ／ 新建 ／ 追加 ／ 改小节 —— ⛔ **删**。
【⛔ 起服 ／ ⛔ 子进程 ／ ⛔ 网络】唯本地件之读 ／ 写（LF ／ UTF-8 ⛔ BOM）。
"""
from core.lib import note_kernel as NK
from core.tools.base import ToolPlugin


class NoteKbPlugin(ToolPlugin):
    name = "note_kb"
    quota = 10

    def validate(self, args):
        return str((args or {}).get("action") or "").strip() in NK.FACES

    def execute(self, args, ctx) -> dict:
        return NK.face(**dict(args or {}))
