#!/usr/bin/env python3
"""User Crypto - User Crypto 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""用户加密模块 - 只有用户能解密"""

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional

from cryptography.fernet import Fernet


class UserCrypto:
    VERSION = "1.0.0"

    def __init__(self, user_id: str, user_key: str):
        self.user_id = user_id
        self.user_dir = Path(
            funified_config.get("paths.users_dir", f"{get_data_root()}/users/")
            + "/{user_id}/encrypted"
        )
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self.cipher = Fernet(self._derive_key(user_key))

    def _derive_key(self, user_key: str) -> bytes:
        """从用户密钥派生 Fernet 密钥"""
        salt_file = self.user_dir / "salt.bin"
        if salt_file.exists():
            salt = salt_file.read_bytes()
        else:
            salt = os.urandom(16)
            salt_file.write_bytes(salt)

        # 使用 PBKDF2 派生密钥（替代方案）
        key = hashlib.pbkdf2_hmac("sha256", user_key.encode(), salt, 100000, 32)
        return base64.urlsafe_b64encode(key)

    def encrypt(self, data: Any, name: str) -> str:
        """加密数据"""
        encrypted = self.cipher.encrypt(json.dumps(data, ensure_ascii=False).encode())
        file_path = self.user_dir / f"{name}.enc"
        file_path.write_bytes(encrypted)
        return str(file_path)

    def decrypt(self, name: str) -> Optional[Any]:
        """解密数据"""
        file_path = self.user_dir / f"{name}.enc"
        if not file_path.exists():
            return None
        decrypted = self.cipher.decrypt(file_path.read_bytes())
        return json.loads(decrypted.decode())

    def list_encrypted(self) -> list:
        """列出加密文件"""
        return [f.stem for f in self.user_dir.glob("*.enc") if f.name != "salt.bin"]


if __name__ == "__main__":
    crypto = UserCrypto("test_user", "password123")
    crypto.encrypt({"test": "data"}, "test")
    print(f"✅ 加密文件: {crypto.list_encrypted()}")
    print(f"✅ 解密: {crypto.decrypt('test')}")
