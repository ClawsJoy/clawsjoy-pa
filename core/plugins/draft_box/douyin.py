# -*- coding: utf-8 -*-
"""抖音草稿插件: 封面 9:16 + 视频相对路径"""
from core.plugins.draft_box.base import DraftBoxPlugin


class DouyinDraftPlugin(DraftBoxPlugin):
    platform = "抖音"
    frontmatter_fields = ("cover",)
    cover_suffix = "9x16"
    media_note = "封面 9:16 竖版; 视频用相对路径引用不复制。"
