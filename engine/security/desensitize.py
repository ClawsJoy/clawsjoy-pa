from typing import Any, Dict, List, Optional

"""脱敏工具 - 敏感数据保护"""

import hashlib
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


class Desensitizer:
    """数据脱敏器"""

    # 敏感信息模式
    PATTERNS = {
        "phone": re.compile(r"1[3-9]\d{9}"),
        "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        "id_card": re.compile(
            r"[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]"
        ),
        "ip": re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"),
        "password": re.compile(
            r'password["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE
        ),
        "token": re.compile(r'token["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE),
        "api_key": re.compile(
            r'api[_-]?key["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE
        ),
        "secret": re.compile(
            r'secret["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE
        ),
    }

    # 脱敏规则
    RULES = {
        "phone": lambda x: x[:3] + "****" + x[-4:],
        "email": lambda x: x[:2] + "***" + x[x.find("@") :],
        "id_card": lambda x: x[:6] + "********" + x[-4:],
        "ip": lambda x: ".".join(x.split(".")[:-1] + ["***"]),
        "password": lambda x: "***REDACTED***",
        "token": lambda x: x[:8] + "..." + x[-8:] if len(x) > 16 else "***REDACTED***",
        "api_key": lambda x: (
            x[:6] + "***" + x[-4:] if len(x) > 10 else "***REDACTED***"
        ),
        "secret": lambda x: "***REDACTED***",
    }

    def __init__(self):
        self.enabled = True
        print("🔒 脱敏器已初始化")

    def desensitize(self, data: Any, level: str = "medium") -> Any:
        """脱敏处理"""
        if not self.enabled:
            return data

        if isinstance(data, str):
            return self._desensitize_string(data, level)
        elif isinstance(data, dict):
            return {k: self.desensitize(v, level) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.desensitize(item, level) for item in data]
        elif isinstance(data, (int, float, bool)):
            return data
        else:
            return str(data)

    def _desensitize_string(self, text: str, level: str) -> str:
        """脱敏字符串"""
        result = text

        for name, pattern in self.PATTERNS.items():

            def replace_match(match, rule_name=name):
                matched = match.group(0)
                if rule_name in self.RULES:
                    return self.RULES[rule_name](matched)
                return "***REDACTED***"

            result = pattern.sub(replace_match, result)

        return result

    def mask_user_id(self, user_id: str) -> str:
        """掩码用户ID"""
        if len(user_id) <= 4:
            return "***"
        return user_id[:2] + "***" + user_id[-2:]

    def hash_sensitive(self, data: str, salt: str = None) -> str:
        """哈希敏感数据（不可逆）"""
        if salt:
            data = data + salt
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def get_stats(self) -> Dict:
        return {"enabled": self.enabled, "patterns": len(self.PATTERNS)}


desensitizer = Desensitizer()
