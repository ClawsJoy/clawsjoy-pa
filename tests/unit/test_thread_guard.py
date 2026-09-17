# -*- coding: utf-8 -*-
"""目标线程硬门测试（2026-09-10 事故驱动）

事故: 第4轮联调发到了【新建线程】而不是老板指定的会话。
本测试锁死: 在任何非会话页面发消息, 都必须被拒绝; 目标 sid 不符也必须被拒绝。
"""
import sys

sys.path.insert(0, ".")
import pytest

sys.path.insert(0, "scripts/agent_client")
import actions as A


class FakePage:
    def __init__(self, url):
        self.url = url


CFG = {
    "deepseek": {
        "send_precondition": {
            "must_match_url": "https://chat.deepseek.com/a/chat/s/{sid}",
            "on_mismatch": "navigate_then_recheck",
            "abort_if_unverified": True,
        },
    },
    "xiaohongshu": {},  # 无该规矩的平台
}


class FakeActions(A.Actions):
    def __init__(self, cfg):
        self.platforms = cfg


SID = "49ad7381-f83b-4745-af63-0ce63c7f2ed1"  # 批195: 与 platforms.py 的 designated_session 一致


def _a():
    return FakeActions(CFG)


def test_blocks_when_not_in_any_thread():
    """事故原样重放: 在基础地址发消息 -> 必须拒绝(否则会新建会话)"""
    r = _a()._thread_guard(FakePage("https://chat.deepseek.com/"), "deepseek", {})
    assert r and "新建会话" in r["error"]


def test_blocks_on_blank_page():
    r = _a()._thread_guard(FakePage("about:blank"), "deepseek", {})
    assert r and "thread_guard 拒绝" in r["error"]


def test_allows_when_inside_a_thread():
    r = _a()._thread_guard(FakePage("https://chat.deepseek.com/a/chat/s/" + SID), "deepseek", {})
    assert r is None


def test_blocks_wrong_thread():
    """指定的 sid 与当前线程不符 -> 拒绝(不把消息发给别人)"""
    other = "5b1c76c0-5b7d-43cc-a9c3-fec667b557a5"
    r = _a()._thread_guard(FakePage("https://chat.deepseek.com/a/chat/s/" + other), "deepseek", {"expect_sid": SID})
    assert r and "目标线程不符" in r["error"]


def test_allows_matching_thread_with_expect_sid():
    r = _a()._thread_guard(FakePage("https://chat.deepseek.com/a/chat/s/" + SID), "deepseek", {"expect_sid": SID})
    assert r is None


def test_explicit_new_thread_optin():
    """确要新建会话必须显式声明 —— 不允许"顺手"新建"""
    r = _a()._thread_guard(FakePage("https://chat.deepseek.com/"), "deepseek", {"allow_new_thread": True})
    assert r is None


def test_platform_without_rule_unaffected():
    """没声明该规矩的平台(如小红书)不受影响 —— 加固不得改坏既有行为"""
    r = _a()._thread_guard(FakePage("https://www.xiaohongshu.com/explore"), "xiaohongshu", {})
    assert r is None


def test_url_with_query_and_hash_still_matches():
    r = _a()._thread_guard(
        FakePage("https://chat.deepseek.com/a/chat/s/" + SID + "?x=1#y"), "deepseek", {"expect_sid": SID}
    )
    assert r is None
