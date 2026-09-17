"""数据脱敏处理器 - 生产环境数据保护"""

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


class DataMaskProcessor:
    """数据脱敏处理器"""

    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict:
        """加载脱敏规则"""
        return {
            "phone": {
                "pattern": r"1[3-9]\d{9}",
                "mask": lambda x: x[:3] + "****" + x[-4:],
            },
            "email": {
                "pattern": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                "mask": lambda x: x[:2] + "***" + x[x.find("@") :],
            },
            "id_card": {
                "pattern": r"[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]",
                "mask": lambda x: x[:6] + "********" + x[-4:],
            },
            "bank_card": {
                "pattern": r"\d{16,19}",
                "mask": lambda x: x[:4] + "****" + x[-4:],
            },
            "password": {
                "pattern": r'password["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                "mask": lambda x: "***REDACTED***",
            },
            "token": {
                "pattern": r"Bearer\s+[A-Za-z0-9\-._~+/]+=*",
                "mask": lambda x: "Bearer ***REDACTED***",
            },
        }

    def mask(self, data: Any, level: str = "medium") -> Any:
        """应用脱敏"""
        if isinstance(data, str):
            return self._mask_string(data)
        elif isinstance(data, dict):
            return {k: self.mask(v, level) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.mask(item, level) for item in data]
        return data

    def _mask_string(self, text: str) -> str:
        """脱敏字符串"""
        result = text
        for rule in self.rules.values():
            result = re.sub(rule["pattern"], lambda m: rule["mask"](m.group(0)), result)
        return result

    def anonymize(self, data: Dict) -> Dict:
        """匿名化（不可逆）"""
        result = data.copy()
        if "user_id" in result:
            result["user_id"] = hashlib.sha256(result["user_id"].encode()).hexdigest()[
                :16
            ]
        if "phone" in result:
            result["phone"] = hashlib.sha256(result["phone"].encode()).hexdigest()[:16]
        if "email" in result:
            result["email"] = hashlib.sha256(result["email"].encode()).hexdigest()[:16]
        return result

    def pseudonymize(self, data: Dict, salt: str) -> Dict:
        """假名化（可逆）"""
        result = data.copy()
        if "user_id" in result:
            result["user_id"] = hashlib.pbkdf2_hmac(
                "sha256", result["user_id"].encode(), salt.encode(), 100000
            ).hex()[:16]
        return result


data_mask = DataMaskProcessor()
