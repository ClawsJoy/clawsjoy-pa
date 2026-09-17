#!/usr/bin/env python3
"""数据脱敏模块"""

import re


class Desensitizer:
    """数据脱敏器"""

    def __init__(self):
        self.patterns = {
            "phone": re.compile(r"1[3-9]\d{9}"),
            "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
            "id_card": re.compile(
                r"[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]"
            ),
            "ip": re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"),
            "password": re.compile(
                r'password["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE
            ),
            "token": re.compile(
                r'token["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE
            ),
            "api_key": re.compile(
                r'api[_-]?key["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE
            ),
        }

    def desensitize(self, text: str) -> str:
        """脱敏处理"""
        if not text or not isinstance(text, str):
            return text

        result = text

        # 手机号脱敏
        result = self.patterns["phone"].sub(
            lambda m: m.group()[:3] + "****" + m.group()[-4:], result
        )

        # 邮箱脱敏
        result = self.patterns["email"].sub(
            lambda m: m.group()[0] + "***" + m.group()[m.group().find("@") :], result
        )

        # 身份证脱敏
        result = self.patterns["id_card"].sub(
            lambda m: m.group()[:6] + "********" + m.group()[-4:], result
        )

        # IP 脱敏
        result = self.patterns["ip"].sub(
            lambda m: m.group().split(".")[0] + ".*.*.*", result
        )

        return result


# 全局实例
desensitizer = Desensitizer()
