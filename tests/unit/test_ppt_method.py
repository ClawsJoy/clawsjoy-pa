# -*- coding: utf-8 -*-
"""PPT 图文生产管线方法论 V0.1 测试（2026-09-10）"""
import sys

sys.path.insert(0, ".")
import pytest

from core.pa import audit as A
from core.pa import ppt_method as P


def test_font_scale_fixed():
    assert P.FONT_SCALE["H1"] > P.FONT_SCALE["H2"] > P.FONT_SCALE["H3"] > P.FONT_SCALE["BODY"]
    assert P.FONT_SCALE["STAT"] >= 64, "关键数字要大字(≥64px)"


def test_image_prompt_suffix_has_hard_constraints():
    s = P.IMAGE_PROMPT_SUFFIX
    assert "16:9" in s and "≥40%" in s
    for banned in ("neon", "gradient", "霓虹", "渐变"):
        assert banned in s, "禁止词必须在 prompt 模板里"


def test_slides_json_generates_video_metadata():
    pages = [{"layout": "stat", "data": {"title": "投资奖励", "number": "10%"}, "voiceover": "投资满两年奖励百分之十"}]
    rows = P.slides_json(pages)
    assert rows[0]["page_type"] == "stat"
    assert rows[0]["stat"] == "10%"
    assert rows[0]["voiceover"] == "投资满两年奖励百分之十"
    assert rows[0]["aspect_ratio"] == "16:9"


def test_voiceover_ok_limits_20_chars():
    assert P.voiceover_ok("投资满两年奖励百分之十")
    assert not P.voiceover_ok("这是一句超过了二十个字的口播文案用来测试字数上限的拦截逻辑是否正确生效")


def test_render_lock_default_true():
    assert P.render_lock([])["render_lock"] is True


def test_preflight_stat_standalone():
    # stat 布局缺 number → fail
    issues = A.preflight([{"layout": "stat", "data": {}}])
    assert any(i[1] == "fail" and "缺关键数字" in i[2] for i in issues)
    # 过长 number → warn
    issues = A.preflight([{"layout": "stat", "data": {"number": "这是一个非常长的数字表述啊"}}])
    assert any(i[1] == "warn" and "独立成行" in i[2] for i in issues)
