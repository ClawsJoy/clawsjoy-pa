#!/usr/bin/env python3
"""Encryption Hook - Encryption Hook 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import base64
import hashlib
import json
import secrets
from pathlib import Path
from typing import Any, Dict, Optional

# 兼容不同版本的 cryptography
try:
    from cryptography.fernet import Fernet

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️ cryptography 未安装，加密功能不可用")


class EncryptionHook:
    """用户数据加密钩子"""

    def __init__(self):
        self.key_file = Path("data/keys/master.key")
        self._load_or_create_key()

    def _load_or_create_key(self):
        """加载或创建主密钥"""
        if not CRYPTO_AVAILABLE:
            self.key = None
            return

        if self.key_file.exists():
            with open(self.key_file, "rb") as f:
                self.key = f.read()
        else:
            self.key_file.parent.mkdir(parents=True, exist_ok=True)
            self.key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(self.key)

    def encrypt(self, data: str) -> Optional[str]:
        """加密数据"""
        if not CRYPTO_AVAILABLE or not self.key:
            return data
        try:
            f = Fernet(self.key)
            return f.encrypt(data.encode()).decode()
        except Exception as e:
            print(f"加密失败: {e}")
            return data

    def decrypt(self, encrypted: str) -> Optional[str]:
        """解密数据"""
        if not CRYPTO_AVAILABLE or not self.key:
            return encrypted
        try:
            f = Fernet(self.key)
            return f.decrypt(encrypted.encode()).decode()
        except Exception as e:
            print(f"解密失败: {e}")
            return encrypted

    def encrypt_dict(self, data: Dict) -> Dict:
        """加密字典中的敏感字段"""
        sensitive_fields = ["password", "secret", "token", "api_key"]
        result = {}
        for key, value in data.items():
            if key.lower() in sensitive_fields and isinstance(value, str):
                result[key] = self.encrypt(value)
            elif isinstance(value, dict):
                result[key] = self.encrypt_dict(value)
            else:
                result[key] = value
        return result


# 全局实例
encryption_hook = EncryptionHook()
