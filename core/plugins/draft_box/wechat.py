# -*- coding: utf-8 -*-
"""公众号草稿插件: 封面 900x383 + summary(120字) + tags"""
from core.plugins.draft_box.base import DraftBoxPlugin


class WechatDraftPlugin(DraftBoxPlugin):
    platform = "公众号"
    frontmatter_fields = ("cover", "summary")
    cover_suffix = "900x383"
    media_note = "封面 900x383; 摘要 ≤120 字; 正文图片用 ![[文件名]] 嵌入。"
