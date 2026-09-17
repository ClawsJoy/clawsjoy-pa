#!/usr/bin/env python3
"""Proxy Helper - Proxy Helper 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""智能代理检测 - 自动选择可用通道"""
import os

import requests


def get_available_proxy():
    """检测可用的代理"""
    proxy_candidates = [
        {
            "http": "http://unified_config.HOST:7890",
            "https": "http://unified_config.HOST:7890",
        },
        {
            "http": "http://unified_config.HOST:10809",
            "https": "http://unified_config.HOST:10809",
        },
        None,  # 直连
    ]

    test_url = "https://source.unsplash.com/featured/"

    for proxy in proxy_candidates:
        try:
            resp = requests.get(test_url, proxies=proxy, timeout=5)
            if resp.status_code == 200:
                print(f"✅ 使用代理: {proxy}")
                return proxy
        except Exception as e:
            continue

    print("⚠️ 无可用代理，使用直连")
    return None


def get_session():
    """获取配置好代理的 session"""
    session = requests.Session()
    proxy = get_available_proxy()
    if proxy:
        session.proxies.update(proxy)
    # 本地地址不走代理
    session.trust_env = False
    return session


def is_local_url(url):
    local_hosts = ["localhost", "127.0.0.1", "0.0.0.0"]
    return any(h in url for h in local_hosts)
