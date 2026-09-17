# -*- coding: utf-8 -*-
"""草稿箱插件注册表 — 平台名 → 插件实例(供 obsidian_knowledge 分发)。"""
from core.plugins.draft_box.base import DraftBoxPlugin
from core.plugins.draft_box.wechat import WechatDraftPlugin
from core.plugins.draft_box.xiaohongshu import XiaohongshuDraftPlugin
from core.plugins.draft_box.zhihu import ZhihuDraftPlugin
from core.plugins.draft_box.bilibili import BilibiliDraftPlugin
from core.plugins.draft_box.douyin import DouyinDraftPlugin

DRAFT_PLUGINS = {
    "公众号": WechatDraftPlugin(),
    "小红书": XiaohongshuDraftPlugin(),
    "知乎": ZhihuDraftPlugin(),
    "B站": BilibiliDraftPlugin(),
    "抖音": DouyinDraftPlugin(),
}


def get_draft_plugin(platform: str):
    """按平台名取插件实例; 未知平台返回 None。"""
    return DRAFT_PLUGINS.get(str(platform or "").strip())


__all__ = ["DraftBoxPlugin", "DRAFT_PLUGINS", "get_draft_plugin"]
