#!/usr/bin/env python3
"""No Proxy - No Proxy 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""强制禁用代理的工具"""
import os

import requests


def disable_proxy():
    """清除所有代理环境变量"""
    for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        os.environ.pop(key, None)
    # 设置 no_proxy
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


def get_session():
    """获取无代理的 requests session"""
    disable_proxy()
    session = requests.Session()
    session.trust_env = False
    return session
