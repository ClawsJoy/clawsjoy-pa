# -*- coding: utf-8 -*-
"""2026-09-13 聊天层参数化收集(纯函数)测试: 规则由字段表驱动, 否定优先。"""
import sys

sys.path.insert(0, ".")
from core.pa.collect import detect_fields, recap_line
from core.pa.profile import FIELD_SCHEMA


def test_rules_only_reference_known_fields_and_options():
    """规则表不能出现字段表之外的字段/取值 —— 字段表是唯一真源。"""
    from core.pa.collect import DETECT_RULES

    for key, rules in DETECT_RULES.items():
        assert key in FIELD_SCHEMA, key
        for opt in rules:
            assert opt in FIELD_SCHEMA[key]["options"], (key, opt)


def test_detects_single_and_multi():
    hits = detect_fields("我是做光电的，喜欢研究技术和市场")
    assert hits["industry"] == "光电"
    assert hits["interests"] == ["技术", "市场"]


def test_negation_wins_over_positive():
    """否定规则必须先匹配: "不要自动写文件" 不能判成 "是"。"""
    assert detect_fields("不要自动写文件")["risk_auto_write"] == "否"
    assert detect_fields("写文件要我确认")["risk_auto_write"] == "否"
    assert detect_fields("自动写文件就行")["risk_auto_write"] == "是"
    assert detect_fields("不要自动执行命令")["risk_auto_exec"] == "否"
    assert detect_fields("外发要确认")["risk_auto_send"] == "否"


def test_no_hit_returns_empty():
    assert detect_fields("今天天气不错") == {}
    assert detect_fields("") == {}
    assert detect_fields(None) == {}


def test_recap_line_is_empty_without_hits():
    assert recap_line({}) == ""
    line = recap_line(detect_fields("汇报详细一点"))
    assert "记下了" in line and "汇报详细度 = 详" in line
