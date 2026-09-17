#!/usr/bin/env python3
"""Private Manager - Private Manager 模块

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

"""私人管家 - 私密数据管理器"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from cryptography.fernet import Fernet


class PrivateManager:
    """私密数据管理器 - 密码、密钥、敏感信息"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.user_dir = Path(
            funified_config.get("paths.users_dir", f"{get_data_root()}/users/")
            + "/{user_id}/private"
        )
        self.user_dir.mkdir(parents=True, exist_ok=True)

        # 加载用户专属密钥
        self._load_key()
        self._load_vault()

    def _load_key(self):
        """加载用户密钥"""
        key_file = self.user_dir / "master.key"
        if key_file.exists():
            self.cipher = Fernet(key_file.read_bytes())
        else:
            # 生成新密钥
            self.cipher = Fernet(Fernet.generate_key())
            key_file.write_bytes(self.cipher._key)

    def _load_vault(self):
        """加载私密保险箱"""
        vault_file = self.user_dir / "vault.json"
        if vault_file.exists():
            encrypted = vault_file.read_bytes()
            decrypted = self.cipher.decrypt(encrypted)
            self.vault = json.loads(decrypted)
        else:
            self.vault = {
                "passwords": {},
                "secrets": {},
                "notes": [],
                "created_at": datetime.now().isoformat(),
            }

    def _save_vault(self):
        """保存私密保险箱"""
        encrypted = self.cipher.encrypt(json.dumps(self.vault).encode())
        vault_file = self.user_dir / "vault.json"
        vault_file.write_bytes(encrypted)

    def add_password(self, service: str, username: str, password: str) -> Dict:
        """添加密码"""
        self.vault["passwords"][service] = {
            "username": username,
            "password": password,  # 实际应用中应再次加密
            "updated_at": datetime.now().isoformat(),
        }
        self._save_vault()
        return {"success": True, "service": service}

    def get_password(self, service: str) -> Dict:
        """获取密码"""
        return self.vault["passwords"].get(service, {})

    def add_secret(self, key: str, value: str) -> Dict:
        """添加密钥"""
        self.vault["secrets"][key] = {
            "value": value,
            "updated_at": datetime.now().isoformat(),
        }
        self._save_vault()
        return {"success": True, "key": key}

    def add_note(self, title: str, content: str) -> Dict:
        """添加私密笔记"""
        self.vault["notes"].append(
            {
                "id": hashlib.md5(
                    f"{title}{datetime.now().isoformat()}".encode()
                ).hexdigest()[:8],
                "title": title,
                "content": content,
                "created_at": datetime.now().isoformat(),
            }
        )
        self._save_vault()
        return {"success": True, "title": title}

    def list_notes(self) -> List[Dict]:
        """列出笔记（仅标题）"""
        return [
            {"id": n["id"], "title": n["title"], "created_at": n["created_at"]}
            for n in self.vault["notes"]
        ]

    def get_note(self, note_id: str) -> Dict:
        """获取笔记内容"""
        for note in self.vault["notes"]:
            if note["id"] == note_id:
                return note
        return {}

    def delete_note(self, note_id: str) -> Dict:
        """删除笔记"""
        self.vault["notes"] = [n for n in self.vault["notes"] if n["id"] != note_id]
        self._save_vault()
        return {"success": True}


def get_private_manager(user_id: str) -> PrivateManager:
    return PrivateManager(user_id)
