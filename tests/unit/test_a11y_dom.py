# -*- coding: utf-8 -*-
"""P1 单测: core/tools/a11y_dom.py — role/label 策略/占位检测/选择器/校验/items_text"""
import sys
sys.path.insert(0, ".")
from core.tools.a11y_dom import (
    role_of, stable_label, is_content_like_placeholder, build_selector,
    dedupe_key, items_text, parse_index, expected_roles_for, validate_selection,
    pick_stable_anchor_for,
)


def test_role_of():
    assert role_of({"tag": "BUTTON"}) == "button"
    assert role_of({"tag": "INPUT", "type": "submit"}) == "button"
    assert role_of({"tag": "INPUT", "type": "text"}) == "input"
    assert role_of({"tag": "INPUT"}) == "input"
    assert role_of({"tag": "TEXTAREA"}) == "textarea"
    assert role_of({"tag": "SELECT"}) == "select"
    assert role_of({"tag": "A"}) == "link"
    assert role_of({"tag": "INPUT", "type": "checkbox"}) == "checkbox"
    assert role_of({"tag": "DIV", "role_attr": "button"}) == "button"
    # P2 发现: 百度新版搜索输入是 div[contenteditable]
    assert role_of({"tag": "DIV", "contenteditable": ""}) == "textbox"
    assert role_of({"tag": "SPAN", "contenteditable": "true"}) == "textbox"
    assert role_of({"tag": "DIV"}) == "other"
    assert stable_label({"tag": "DIV", "contenteditable": ""}) == ("文本输入框", "role-desc")


def test_stable_label_priority():
    # aria > 关联 label > title/alt > 文本 > placeholder(静态) > role 描述
    assert stable_label({"aria_label": "关闭", "tag": "BUTTON", "inner_text": "x"}) == ("关闭", "aria")
    assert stable_label({"label_for_text": "用户名", "tag": "INPUT"}) == ("用户名", "label")
    assert stable_label({"title": "帮助", "tag": "A"}) == ("帮助", "title/alt")
    assert stable_label({"tag": "BUTTON", "inner_text": "  百度一下  "}) == ("百度一下", "text")
    assert stable_label({"tag": "A", "inner_text": "新闻"}) == ("新闻", "text")
    # 静态描述性占位可用
    assert stable_label({"tag": "INPUT", "type": "text", "placeholder": "请输入搜索内容"}) == ("请输入搜索内容", "placeholder")


def test_stable_label_content_like_placeholder_not_used():
    # POC 失败案例: 新闻式滚动占位不得当标签 → 稳定描述兜底
    el = {"tag": "INPUT", "type": "text", "placeholder": "普京称支持全面恢复俄美关系"}
    label, src = stable_label(el)
    assert src == "role-desc" and "占位" not in label and label == "文本输入框", (label, src)
    # search 型 + 内容化占位 → 搜索输入框
    el2 = {"tag": "INPUT", "type": "search", "placeholder": "普京称支持全面恢复俄美关系"}
    assert stable_label(el2)[0] == "搜索输入框"
    # search 型 + 静态描述占位(如 搜索您感兴趣的内容) → 占位可用
    el2b = {"tag": "INPUT", "type": "search", "placeholder": "搜索您感兴趣的内容"}
    assert stable_label(el2b)[1] == "placeholder"
    # textarea 无占位 → 多行文本输入框
    assert stable_label({"tag": "TEXTAREA"}) == ("多行文本输入框", "role-desc")
    # 纯图标按钮无文本 → 按钮
    assert stable_label({"tag": "BUTTON"}) == ("按钮", "role-desc")


def test_is_content_like_placeholder():
    assert is_content_like_placeholder("普京称支持全面恢复俄美关系") is True   # 实体动作词
    assert is_content_like_placeholder("周健任成都市龙泉驿区委书记") is True   # 新闻式人名内容(无数字/动作词)
    assert is_content_like_placeholder("5烧水喝和买桶装水喝 哪个更健康") is True  # 数字
    assert is_content_like_placeholder("上海和平饭店回应一杯椰汁50元") is True    # 数字
    assert is_content_like_placeholder("这是一段超过二十五个字符的很长很长的占位描述文字内容呀") is True  # 超长
    assert is_content_like_placeholder("请输入搜索内容") is False   # 静态指令前缀
    assert is_content_like_placeholder("搜索您感兴趣的内容") is False  # 静态指令前缀
    assert is_content_like_placeholder("搜索") is False
    assert is_content_like_placeholder("你的邮箱") is False


def test_build_selector():
    assert build_selector([{"tag": "INPUT", "id": "kw"}]) == "#kw"
    assert build_selector([{"tag": "BUTTON", "id": "su"}]) == "#su"
    assert build_selector([{"tag": "BUTTON", "attrs": {"data-test": "submit"}}]) == 'button[data-test="submit"]'
    assert build_selector([{"tag": "A", "idx": 2}, {"tag": "LI", "idx": 0}, {"tag": "UL"}]) == "a:nth-of-type(3) > li:nth-of-type(1) > ul"
    assert build_selector([{"tag": "DIV"}]) == "div"
    assert build_selector([]) == ""


def test_dedupe_key_stable_and_distinct():
    a = {"tag": "BUTTON", "label": "百度一下", "sel": "#su"}
    b = {"tag": "BUTTON", "label": "百度一下", "sel": "#su"}
    c = {"tag": "A", "label": "新闻", "sel": "a:nth-of-type(1)"}
    assert dedupe_key(a) == dedupe_key(b)
    assert dedupe_key(a) != dedupe_key(c)


def test_items_text_plain_and_shuffled():
    items = [
        {"role": "button", "label": "百度一下"},
        {"role": "input", "label": "搜索输入框"},
        {"role": "link", "label": "新闻"},
    ]
    text, order = items_text(items)
    assert order is None
    assert text == "1|button|百度一下\n2|input|搜索输入框\n3|link|新闻"
    text2, order2 = items_text(items, seed=7)
    assert order2 is not None and sorted(order2.values()) == [1, 2, 3], order2
    assert sorted(order2.keys()) == [1, 2, 3]
    # 双检: 打乱后文本首行不再是固定原序号
    assert text2 != text


def test_parse_index():
    assert parse_index("1") == 1
    assert parse_index("我选 2 号") == 2
    assert parse_index("0") == 0
    assert parse_index("找不到匹配") is None
    assert parse_index("") is None
    assert parse_index(None) is None


def test_expected_roles_for():
    assert "button" in expected_roles_for("click") and "link" in expected_roles_for("click")
    assert {"input", "textarea", "textbox", "searchbox"} <= expected_roles_for("fill")
    assert "select" in expected_roles_for("select_option")


def test_validate_selection():
    roles = ["button", "input", "link", "button"]
    assert validate_selection(1, 4, action="click", items_roles=roles)["ok"] is True
    assert validate_selection(None, 4)["ok"] is False          # 非整数
    assert validate_selection(0, 4)["ok"] is False             # 找不到
    assert validate_selection(5, 4)["ok"] is False             # 越界
    # role 不匹配: click 目标却是 input(文本)
    r = validate_selection(2, 4, action="click", items_roles=roles)
    assert r["ok"] is False and "不匹配" in r["reason"]
    # fill 目标 link → 拒绝
    assert validate_selection(3, 4, action="fill", items_roles=roles)["ok"] is False
    # 无动作时只做值域
    assert validate_selection(4, 4)["ok"] is True


def test_pick_stable_anchor():
    items = [
        {"role": "button", "label": "百度一下"},
        {"role": "input", "label": "文本输入框"},
        {"role": "link", "label": "新闻"},
    ]
    assert pick_stable_anchor_for(items, "button", ["百度"]) == [1]
    assert pick_stable_anchor_for(items, "input", ["搜索"]) == []
