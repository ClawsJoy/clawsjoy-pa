#!/usr/bin/env python3
"""Safety - Safety 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import re
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse


class SafetyChecker:
    """安全合规检查器"""

    # 敏感域名黑名单
    BLACKLIST_DOMAINS = [
        "weibo.com",
        "weixin.com",
        "qq.com",  # 社交平台
        "baidu.com",
        "google.com",  # 搜索引擎
        "taobao.com",
        "jd.com",  # 电商
        "douyin.com",
        "kuaishou.com",  # 短视频
    ]

    # 敏感关键词
    SENSITIVE_KEYWORDS = [
        "password",
        "token",
        "secret",
        "key",
        "身份证",
        "手机号",
        "银行卡",
        "密码",
        "private",
        "confidential",
    ]

    # 允许的域名白名单（用户配置）
    @classmethod
    def load_whitelist(cls) -> List[str]:
        """加载白名单"""
        whitelist_file = Path("config/collector_whitelist.txt")
        if whitelist_file.exists():
            return [
                line.strip()
                for line in whitelist_file.read_text().splitlines()
                if line.strip()
            ]
        return [
            "info.gov.hk",
            "edb.gov.hk",
            "immd.gov.hk",  # 香港政府
            "labour.gov.hk",
            "ha.org.hk",  # 公共服务
        ]

    @classmethod
    def check_url(cls, url: str) -> Tuple[bool, str]:
        """检查URL是否合规"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # 1. 黑名单检查
            for black in cls.BLACKLIST_DOMAINS:
                if black in domain:
                    return False, f"域名 {domain} 在黑名单中"

            # 2. 白名单检查（可选）
            whitelist = cls.load_whitelist()
            if whitelist and not any(w in domain for w in whitelist):
                # 非白名单域名需要特殊处理
                return False, f"域名 {domain} 不在白名单中，需要用户授权"

            # 3. 协议检查
            if parsed.scheme not in ["http", "https"]:
                return False, f"不支持的协议: {parsed.scheme}"

            return True, "合规"

        except Exception as e:
            return False, f"URL解析失败: {e}"

    @classmethod
    def check_content(cls, content: str) -> Tuple[bool, str]:
        """检查内容是否包含敏感信息"""
        content_lower = content.lower()
        for keyword in cls.SENSITIVE_KEYWORDS:
            if keyword.lower() in content_lower:
                return False, f"包含敏感关键词: {keyword}"
        return True, "合规"

    @classmethod
    def need_user_consent(cls, url: str, user_id: str = None) -> bool:
        """是否需要用户授权"""
        # 非白名单域名需要用户授权
        whitelist = cls.load_whitelist()
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if not any(w in domain for w in whitelist):
            return True
        return False


safety_checker = SafetyChecker()
