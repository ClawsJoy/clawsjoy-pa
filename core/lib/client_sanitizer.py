#!/usr/bin/env python3
"""Client Sanitizer - Client Sanitizer 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


#!/usr/bin/env python3
"""客户端脱敏钩子 - 用户端执行，源文件不上传"""

import json
import re
from typing import Any, Dict, Optional, Tuple


class ClientSanitizer:
    """客户端脱敏 - 在用户本地执行"""

    VERSION = "1.0.0"

    # 需要脱敏的信息类型
    SENSITIVE_PATTERNS = {
        "id_card": r"\d{17}[\dXx]",
        "phone": r"1[3-9]\d{9}",
        "email": r"\S+@\S+\.\S+",
        "address": r"(省|市|区|县|镇|村|路|街|号)\S*",
        "name": r"[姓][一二三四五六七八九十大小]",
        "api_key": r"[a-zA-Z0-9]{32,}",
        "password": r"password[=:]\S+",
        "token": r"token[=:]\S+",
    }

    # 替换模板
    REPLACEMENTS = {
        "id_card": "[身份证]",
        "phone": "[手机号]",
        "email": "[邮箱]",
        "address": "[地址]",
        "name": "[姓名]",
        "api_key": "[API_KEY]",
        "password": "[PASSWORD]",
        "token": "[TOKEN]",
    }

    def sanitize(self, text: str, level: str = "high") -> Tuple[str, Dict]:
        """
        脱敏处理
        level: high(高), medium(中), low(低)
        """
        original = text
        redacted = text
        detected = {}

        for pattern_name, pattern in self.SENSITIVE_PATTERNS.items():
            matches = re.findall(pattern, redacted, re.IGNORECASE)
            if matches:
                detected[pattern_name] = len(matches)
                replacement = self.REPLACEMENTS.get(pattern_name, "[敏感信息]")
                redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)

        # 额外处理：移除连续数字（可能是身份证号片段）
        if level == "high":
            redacted = re.sub(r"\d{5,}", "[数字]", redacted)

        return redacted, {
            "original_length": len(original),
            "redacted_length": len(redacted),
            "detected": detected,
            "level": level,
        }

    def sanitize_message(self, message: Dict) -> Tuple[Dict, Dict]:
        """脱敏消息"""
        sanitized = message.copy()
        stats = {"total_redactions": 0}

        # 脱敏用户输入
        if "user_input" in sanitized:
            redacted, info = self.sanitize(sanitized["user_input"])
            sanitized["user_input"] = redacted
            sanitized["_sanitized"] = True
            stats["user_input_redactions"] = info["detected"]
            stats["total_redactions"] += sum(info["detected"].values())

        # 脱敏参数中的 prompt
        if "params" in sanitized and "prompt" in sanitized["params"]:
            redacted, info = self.sanitize(sanitized["params"]["prompt"])
            sanitized["params"]["prompt"] = redacted
            stats["prompt_redactions"] = info["detected"]
            stats["total_redactions"] += sum(info["detected"].values())

        return sanitized, stats

    def can_send_to_server(self, text: str) -> bool:
        """检查是否可以发送到服务器（无敏感信息残留）"""
        redacted, info = self.sanitize(text)
        # 如果还有未脱敏的敏感模式，不能发送
        for pattern in self.SENSITIVE_PATTERNS.values():
            if re.search(pattern, redacted, re.IGNORECASE):
                return False
        return True


client_sanitizer = ClientSanitizer()


if __name__ == "__main__":
    print(f"客户端脱敏钩子 v{client_sanitizer.VERSION}")

    # 测试
    test_input = "我叫张三，电话13812345678，身份证123456789012345678，帮我生成漫剧人物"

    print(f"\n原始: {test_input}")
    redacted, stats = client_sanitizer.sanitize(test_input)
    print(f"脱敏: {redacted}")
    print(f"统计: {stats}")

    can_send = client_sanitizer.can_send_to_server(test_input)
    print(f"\n可发送到服务器: {can_send}")
