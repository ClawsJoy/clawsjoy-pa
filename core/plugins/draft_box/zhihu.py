# -*- coding: utf-8 -*-
"""知乎草稿插件: 无摘要, 可选封面"""
from core.plugins.draft_box.base import DraftBoxPlugin


class ZhihuDraftPlugin(DraftBoxPlugin):
    platform = "知乎"
    frontmatter_fields = ()
    cover_suffix = "16x9"
    media_note = "无摘要, 可选封面; 正文可带配图。"
