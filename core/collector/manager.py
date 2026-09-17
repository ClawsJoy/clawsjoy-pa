#!/usr/bin/env python3
"""Manager - Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import time
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

import requests

from core.lib.unified_config import unified_config

from .safety import safety_checker


class CollectorManager:
    """采集管理器 - 安全、合规、智能"""

    VERSION = "1.0.0"

    def __init__(self):
        self.lock = Lock()
        self.stats = {
            "total_requests": 0,
            "blocked": 0,
            "success": 0,
            "failed": 0,
            "last_request": None,
        }
        self.user_consents = {}  # user_id -> {domain: consented}
        print(f"🛡️ 采集管理器 v{self.VERSION} 已启动（合规模式）")

    def collect(
        self, url: str, user_id: str = None, force: bool = False
    ) -> Optional[str]:
        """安全采集单个URL"""
        with self.lock:
            self.stats["total_requests"] += 1
            self.stats["last_request"] = datetime.now().isoformat()

        # 1. 安全检查
        is_safe, reason = safety_checker.check_url(url)
        if not is_safe and not force:
            self.stats["blocked"] += 1
            print(f"🚫 采集被阻止: {reason}")
            return None

        # 2. 用户授权检查
        if safety_checker.need_user_consent(url, user_id):
            if not self._has_consent(user_id, url):
                print(f"🔐 需要用户授权: {url}")
                return None

        # 3. 频率限制
        if not self._check_rate_limit():
            print(f"⏱️ 频率限制，跳过: {url}")
            return None

        # 4. 执行采集
        try:
            resp = requests.get(
                url,
                timeout=config_helper.get_timeout("default"),
                headers={
                    "User-Agent": "ClawsJoy-Bot/1.0 (Compliant)",
                    "Accept": "text/html,application/xhtml+xml",
                },
            )

            if resp.status_code == 200:
                content = resp.text[:5000]  # 限制长度

                # 5. 内容安全检查
                is_safe, reason = safety_checker.check_content(content)
                if not is_safe:
                    self.stats["blocked"] += 1
                    print(f"⚠️ 内容被过滤: {reason}")
                    return None

                self.stats["success"] += 1
                return content
            else:
                self.stats["failed"] += 1
                return None

        except Exception as e:
            self.stats["failed"] += 1
            print(f"❌ 采集失败: {e}")
            return None

    def _check_rate_limit(self) -> bool:
        """检查频率限制"""
        config = unified_config.get("thresholds.spider", {})
        delay = config.get("delay_between_requests", 1)

        if self.stats["last_request"]:
            last = datetime.fromisoformat(self.stats["last_request"])
            if (datetime.now() - last).total_seconds() < delay:
                return False
        return True

    def _has_consent(self, user_id: str, url: str) -> bool:
        """检查用户授权"""
        if not user_id:
            return False
        from urllib.parse import urlparse

        domain = urlparse(url).netloc
        return self.user_consents.get(user_id, {}).get(domain, False)

    def grant_consent(self, user_id: str, domain: str):
        """用户授权"""
        if user_id not in self.user_consents:
            self.user_consents[user_id] = {}
        self.user_consents[user_id][domain] = True
        print(f"✅ 用户 {user_id} 授权采集: {domain}")

    def get_stats(self) -> Dict:
        """获取统计"""
        return self.stats


collector_manager = CollectorManager()
