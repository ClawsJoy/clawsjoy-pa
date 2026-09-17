#!/usr/bin/env python3
"""Security Hook - Security Hook 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""安全钩子 - 配置驱动版"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from core.lib.config_loader import config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SecurityHook:
    """安全钩子 - 配置驱动"""

    VERSION = "1.0.0"

    def __init__(self):
        self._load_config()
        self.violation_log = Path(
            self.audit_config.get("log_file", "logs/security_violations.log")
        )
        self.violation_log.parent.mkdir(parents=True, exist_ok=True)
        self.violation_count = 0

    def _load_config(self):
        """从配置加载安全规则"""
        # 从 YAML 文件直接加载，避免 config_loader 点号问题
        config_file = Path("config/driver/security.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                data = unified_config.get("security_hook", {})
                self.enabled = data.get("enabled", True)
                self.patterns = data.get("patterns", {})
                self.blocked_content = data.get("blocked_content", [])
                self.blocked_responses = data.get("blocked_responses", [])
                self.allowed_topics = data.get("allowed_topics", [])
                self.safe_responses = data.get("safe_responses", {})
                self.audit_config = data.get("audit", {})
                self.alert_config = data.get("alert", {})
        else:
            # 默认配置
            self.enabled = True
            self.patterns = {}
            self.blocked_content = []
            self.blocked_responses = []
            self.allowed_topics = []
            self.safe_responses = {}
            self.audit_config = {}
            self.alert_config = {}

        # 编译正则表达式
        self.compiled_patterns = {}
        for category, pattern_list in self.patterns.items():
            self.compiled_patterns[category] = [
                re.compile(p, re.IGNORECASE) for p in pattern_list
            ]

    def check_input(self, text: str) -> Tuple[bool, str, str]:
        """检查输入内容"""
        if not self.enabled or not text:
            return True, "", ""

        # 检查白名单
        for topic in self.allowed_topics:
            if topic in text:
                return True, "", ""

        # 检查敏感词模式
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    reason = f"匹配{category}类敏感词"
                    self._log_violation(text, reason, "input")
                    return (
                        False,
                        category,
                        self.safe_responses.get(category, "内容不合规"),
                    )

        # 检查禁止内容
        for blocked in self.blocked_content:
            if blocked in text:
                self._log_violation(text, f"禁止内容: {blocked}", "input")
                return (
                    False,
                    "blocked",
                    self.safe_responses.get("default", "内容不合规"),
                )

        return True, "", ""

    def check_output(self, text: str) -> Tuple[bool, str]:
        """检查输出内容"""
        if not self.enabled or not text:
            return True, ""

        # 检查禁止回复
        for blocked in self.blocked_responses:
            if blocked in text:
                self._log_violation(text, f"禁止回复: {blocked}", "output")
                return False, "禁止回复内容"

        return True, ""

    def check_message(self, message: Dict) -> Tuple[bool, Optional[Dict]]:
        """检查消息"""
        # 检查用户输入
        user_input = message.get("data", {}).get("user_input", "")
        if user_input:
            safe, category, response = self.check_input(user_input)
            if not safe:
                return False, {
                    "action": "security_error",
                    "error": "security_violation",
                    "category": category,
                    "message": response,
                }

        # 检查生成的 prompt
        prompt = message.get("data", {}).get("params", {}).get("prompt", "")
        if prompt:
            safe, category, response = self.check_input(prompt)
            if not safe:
                return False, {
                    "action": "security_error",
                    "error": "security_violation",
                    "category": category,
                    "message": response,
                }

        return True, None

    def _log_violation(self, content: str, reason: str, category: str):
        """记录违规"""
        self.violation_count += 1
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "content": content[:200],
            "reason": reason,
            "category": category,
        }

        if self.audit_config.get("enabled", True):
            with open(self.violation_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        # 告警
        threshold = self.alert_config.get("threshold", 5)
        if self.violation_count >= threshold:
            logger.warning(f"🔔 安全告警! 违规次数已达 {self.violation_count}")

    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "version": self.VERSION,
            "enabled": self.enabled,
            "violation_count": self.violation_count,
            "patterns_count": sum(len(v) for v in self.patterns.values()),
            "alert_threshold": self.alert_config.get("threshold", 5),
        }


security_hook = SecurityHook()


if __name__ == "__main__":
    print(f"安全钩子 v{security_hook.VERSION}")

    # 测试
    test_inputs = [
        "我想要漫剧人物",
        "香港高才通申请条件",
    ]

    for inp in test_inputs:
        safe, category, response = security_hook.check_input(inp)
        print(f"输入: {inp[:30]}... -> 安全: {safe}, 类别: {category}")

    print(f"\n统计: {security_hook.get_stats()}")
