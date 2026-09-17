# -*- coding: utf-8 -*-
"""小红书草稿插件: 封面 1080x1440 + tags(3-5 话题)"""
from core.plugins.draft_box.base import DraftBoxPlugin


class XiaohongshuDraftPlugin(DraftBoxPlugin):
    platform = "小红书"
    frontmatter_fields = ("cover",)
    cover_suffix = "1080x1440"
    media_note = "封面 1080x1440(3:4 竖版); 3-5 个话题标签。"
