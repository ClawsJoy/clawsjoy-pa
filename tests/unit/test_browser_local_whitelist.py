# -*- coding: utf-8 -*-
"""2026-09-07: browser_local 域名白名单 — 新增飞书文档 bytedance.larkoffice.com。
服务端 core/tools/browser_local.py navigate/search 走 _host_allowed 校验(唯一权威);
python-client 无本地白名单, 白名单在 config/v9/execution_policy.yaml + 代码兜底默认。"""
import sys

sys.path.insert(0, ".")
import pytest

from core.lib.v8 import browser_local as bl


def test_larkoffice_allowed():
    """飞书文档主域放行"""
    assert bl._host_allowed("bytedance.larkoffice.com") is True


def test_larkoffice_subdomain_allowed():
    """飞书文档子域(www/wiki 等)放行"""
    assert bl._host_allowed("www.bytedance.larkoffice.com") is True
    assert bl._host_allowed("wiki.bytedance.larkoffice.com") is True


def test_larkoffice_in_whitelist_list():
    """白名单列表包含飞书文档(yaml 或代码兜底)"""
    assert any(w == "bytedance.larkoffice.com" for w in bl._whitelist())


def test_non_whitelisted_still_blocked():
    """未白名单域仍拒绝"""
    assert bl._host_allowed("example.com") is False
    assert bl._host_allowed("evil-larkoffice.com") is False


def test_blacklist_still_blocked():
    """硬黑名单仍拒绝(即使域名相似)"""
    assert bl._host_allowed("drive.google.com") is False


def test_platform_regression():
    """既有平台域不受影响"""
    for h in ("www.douyin.com", "kol.fanqieopen.com", "mp.weixin.qq.com", "www.xiaohongshu.com"):
        assert bl._host_allowed(h) is True, h
