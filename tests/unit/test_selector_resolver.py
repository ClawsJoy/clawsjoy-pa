# -*- coding: utf-8 -*-
"""选择器自愈解析回归测试（2026-09-10）

对应真实事故: @DS Chat 联调第 1 轮点错按钮 → 消息没发出去且不报错。
契约:
  1. 角色选择器命中 >1 → 不盲点第一个, 走 fallback; 全不唯一 → 拒绝执行(fail closed)
  2. 非角色选择器(自由选择器, 如列表卡片) → 保持原行为, 不受影响
  3. 主选择器不可用但 fallback 可用 → 自愈成功并标记 healed
"""
import sys

sys.path.insert(0, ".")

import pytest

sys.path.insert(0, "scripts/agent_client")
import selector_resolver as SR


class FakeLocator:
    def __init__(self, n):
        self._n = n

    def count(self):
        return self._n


class FakeTarget:
    """按选择器返回命中数; evaluate 返回空诊断。"""

    def __init__(self, mapping):
        self.mapping = mapping

    def locator(self, sel):
        return FakeLocator(self.mapping.get(sel, 0))

    def evaluate(self, js, sel):
        return {"count": self.mapping.get(sel, 0), "candidates": []}


CFG = {
    "input_selector": "textarea[placeholder*='发送消息']",
    "submit_selector": "div._hash div[class*='circle']",
    "submit_selector_fallbacks": ["div._hash div[class*='filled']", "div.ds-button--circle.ds-button--primary"],
    "card_selector": "section.note-item",
}

DS_SUB = "div._hash div[class*='circle']"


def test_role_detection():
    assert SR.role_of_selector(CFG, DS_SUB) == "submit_selector"
    assert SR.role_of_selector(CFG, "div._hash div[class*='filled']") == "submit_selector"
    assert SR.role_of_selector(CFG, "section.note-item") == "card_selector"
    assert SR.role_of_selector(CFG, "div.something-random") is None


def test_candidates_order_primary_first():
    c = SR.candidates_for(CFG, "submit_selector")
    assert c[0] == DS_SUB
    assert "div._hash div[class*='filled']" in c
    assert len(c) == len(set(c)), "候选去重"


def test_free_selector_untouched():
    """自由选择器必须保持原行为 —— 不能因唯一性校验改坏既有流程"""
    t = FakeTarget({"div.something-random": 5})
    sel, diag = SR.resolve_for_action(t, CFG, "div.something-random", "click")
    assert sel == "div.something-random"
    assert diag["strict"] is False


def test_multi_instance_role_never_strict():
    """单测抓出的设计缺陷: 列表卡片/回复容器命中多个是【正常语义】, 不得拒绝"""
    t = FakeTarget({"section.note-item": 20})
    sel, diag = SR.resolve_for_action(t, CFG, "section.note-item", "click")
    assert sel == "section.note-item", "列表卡片必须照旧点第一个"
    assert diag["strict"] is False and diag["reason"] == "multi-instance-role"

    cfg2 = dict(CFG, reply_selector=".ds-markdown")
    t2 = FakeTarget({".ds-markdown": 4})
    sel2, diag2 = SR.resolve_for_action(t2, cfg2, ".ds-markdown", "extract")
    assert sel2 == ".ds-markdown", "多轮对话的回复容器也是多实例, 不得拒绝"


def test_unique_primary_used_directly():
    t = FakeTarget({DS_SUB: 1})
    sel, diag = SR.resolve_for_action(t, CFG, DS_SUB, "click")
    assert sel == DS_SUB and diag["strict"] is True and not diag.get("healed")


def test_ambiguous_primary_falls_back():
    """主选择器命中 2 个(真实事故场景) → 用 fallback 里唯一的那个, 且标记 healed"""
    t = FakeTarget({DS_SUB: 2, "div._hash div[class*='filled']": 1})
    sel, diag = SR.resolve_for_action(t, CFG, DS_SUB, "click")
    assert sel == "div._hash div[class*='filled']"
    assert diag["healed"] is True


def test_all_ambiguous_fails_closed():
    """全部候选都不唯一 → 必须拒绝执行, 不能盲点第一个"""
    t = FakeTarget({DS_SUB: 2, "div._hash div[class*='filled']": 3, "div.ds-button--circle.ds-button--primary": 4})
    sel, diag = SR.resolve_for_action(t, CFG, DS_SUB, "click")
    assert sel is None
    assert diag["error"] == "no unique candidate"
    msg = SR.describe_failure("click", diag)
    assert "fail closed" in msg and "不盲点第一个" in msg


def test_missing_primary_falls_back():
    t = FakeTarget({DS_SUB: 0, "div._hash div[class*='filled']": 1})
    sel, diag = SR.resolve_for_action(t, CFG, DS_SUB, "click")
    assert sel == "div._hash div[class*='filled']"


def test_input_role_strict():
    t = FakeTarget({"textarea[placeholder*='发送消息']": 2})
    sel, diag = SR.resolve_for_action(t, CFG, "textarea[placeholder*='发送消息']", "fill")
    assert sel is None, "输入框命中多个也必须拒绝, 防止填错框"
