# -*- coding: utf-8 -*-
"""douyin 搜索页选择器校准(2026-09-05 真机实测, session douyin_cal)防回归:
platforms.py douyin 段必须用校准后的稳定选择器, 防止旧失效选择器回滚。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agent_client"))

from platforms import load_platforms


def test_douyin_card_selector_calibrated():
    """旧 [data-e2e='search-result-item'] 已失效(页面无此标记) → 必须是 .search-result-card。"""
    cfg = load_platforms()["douyin"]
    assert cfg["card_selector"] == ".search-result-card"
    assert "search-result-item" not in cfg["card_selector"]
    assert "data-e2e" not in cfg["card_selector"]


def test_douyin_link_selector_present():
    """卡片整卡链接锚点 a[href*='/video/'](href 尾段=视频 id)。"""
    cfg = load_platforms()["douyin"]
    assert cfg.get("link_selector") == "a[href*='/video/']"


def test_douyin_search_url_preserved():
    cfg = load_platforms()["douyin"]
    assert "{q}" in cfg["search_url"]
    assert "douyin.com/search" in cfg["search_url"]


def test_douyin_calibration_comment_anchored():
    """校准注释存在(标明真机校准日期), 防后续误删校准依据。"""
    import platforms as _p

    src = _p.__file__
    text = Path(src).read_text(encoding="utf-8")
    i = text.find('"douyin": {')
    seg = text[i : i + 2000]
    assert "2026-09-05 搜索页真机校准" in seg
    assert ".search-result-card" in seg
