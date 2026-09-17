#!/usr/bin/env python3
"""User Secret Manager - User Secret Manager 模块

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
"""用户密钥管理器 - 用户隔离"""

import json
import pickle
from pathlib import Path
from typing import Any, Dict, Optional


class UserSecretManager:
    VERSION = "1.0.0"

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.user_dir = Path(
            funified_config.get("paths.users_dir", f"{get_data_root()}/users/")
            + "/{user_id}/secrets"
        )
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self.keys_file = self.user_dir / "keys.json"
        self.tokens_file = self.user_dir / "tokens.pickle"
        self._load()

    def _load(self):
        if self.keys_file.exists():
            with open(self.keys_file, "r") as f:
                self.keys = json.load(f)
        else:
            self.keys = {}

        if self.tokens_file.exists():
            with open(self.tokens_file, "rb") as f:
                self.tokens = pickle.load(f)
        else:
            self.tokens = {}

    def _save(self):
        with open(self.keys_file, "w") as f:
            json.dump(self.keys, f, indent=2)
        with open(self.tokens_file, "wb") as f:
            pickle.dump(self.tokens, f)

    def set_api_key(self, service: str, key: str):
        self.keys[service] = key
        self._save()

    def get_api_key(self, service: str) -> Optional[str]:
        return self.keys.get(service)

    def set_token(self, service: str, token: Any):
        self.tokens[service] = token
        self._save()

    def get_token(self, service: str) -> Optional[Any]:
        return self.tokens.get(service)

    def get_status(self) -> Dict:
        return {
            "user_id": self.user_id,
            "has_keys": len(self.keys) > 0,
            "has_tokens": len(self.tokens) > 0,
        }


if __name__ == "__main__":
    sm = UserSecretManager("test_user")
    sm.set_api_key("test", "api_key_123")
    print(f"API Key: {sm.get_api_key('test')}")
    print(f"状态: {sm.get_status()}")
