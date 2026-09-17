# -*- coding: utf-8 -*-
"""B站草稿插件: 封面 16:9 + 分区 + 视频相对路径"""
from core.plugins.draft_box.base import DraftBoxPlugin


class BilibiliDraftPlugin(DraftBoxPlugin):
    platform = "B站"
    frontmatter_fields = ("cover", "分区")
    cover_suffix = "16x9"
    media_note = "封面 16:9; 分区(知识/科技/生活等); 视频用相对路径引用不复制。"
