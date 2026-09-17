#!/usr/bin/env python3
"""Unified Data Manager - Unified Data Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict

from core.lib.unified_config import unified_config


class UnifiedDataManager:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.data_root = Path("data")
        self.butler_path = self.data_root / f"butler/{user_id}"
        self.conversation_path = self.data_root / f"users/{user_id}/butler_v2"
        self.butler_path.mkdir(parents=True, exist_ok=True)
        self.conversation_path.mkdir(parents=True, exist_ok=True)

    def save_butler_identity(self, identity: Dict) -> bool:
        identity["updated_at"] = datetime.now().isoformat()
        identity["user_id"] = self.user_id
        identity_file = self.butler_path / "identity.json"
        temp_file = identity_file.with_suffix(".tmp")
        with open(temp_file, "w") as f:
            json.dump(identity, f, indent=2, ensure_ascii=False)
        temp_file.replace(identity_file)
        self._sync_to_conversation(identity)
        return True

    def _sync_to_conversation(self, identity: Dict):
        memory_file = self.conversation_path / "memory.json"
        memory = json.load(open(memory_file)) if memory_file.exists() else {}
        memory["butler"] = {
            "name": identity.get("name"),
            "name_changed_at": identity.get("updated_at"),
        }
        with open(memory_file, "w") as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)

    def get_butler_identity(self) -> Dict:
        identity_file = self.butler_path / "identity.json"
        if identity_file.exists():
            return json.load(open(identity_file))
        return {"name": "小管"}


_data_managers = {}


def get_data_manager(user_id: str):
    if user_id not in _data_managers:
        _data_managers[user_id] = UnifiedDataManager(user_id)
    return _data_managers[user_id]
