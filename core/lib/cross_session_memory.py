#!/usr/bin/env python3
"""Cross Session Memory - Cross Session Memory 模块

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
"""简化版跨会话记忆 - 避免编码问题"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class CrossSessionMemory:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.user_dir = Path(
            unified_config.get("paths.users_dir", f"{get_data_root()}/users/")
            + "/{user_id}/memory"
        )
        self.user_dir.mkdir(parents=True, exist_ok=True)

        self.name = None
        self.preferences = []
        self.interactions = 0
        self._load()

    def _load(self):
        # 简化：只读名字文件
        name_file = self.user_dir / "name.txt"
        if name_file.exists():
            self.name = name_file.read_text(encoding="utf-8", errors="ignore").strip()

        pref_file = self.user_dir / "preferences.txt"
        if pref_file.exists():
            self.preferences = [
                p
                for p in pref_file.read_text(encoding="utf-8", errors="ignore").split(
                    "\n"
                )
                if p
            ]

        count_file = self.user_dir / "count.txt"
        if count_file.exists():
            try:
                self.interactions = int(count_file.read_text().strip())
            except Exception as e:
                self.interactions = 0

    def _save(self):
        if self.name:
            with open(self.user_dir / "name.txt", "w", encoding="utf-8") as f:
                f.write(self.name)

        if self.preferences:
            with open(self.user_dir / "preferences.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(self.preferences))

        with open(self.user_dir / "count.txt", "w") as f:
            f.write(str(self.interactions))

    def remember(self, key: str, value):
        if key == "name":
            self.name = value
        elif key == "preference":
            if value not in self.preferences:
                self.preferences.append(value)
        self._save()

    def record_interaction(self, user_input: str, response: str, task: str = None):
        self.interactions += 1
        self._save()

    def recall(self, query: str = None) -> Dict:
        return {
            "name": self.name,
            "preferences": self.preferences,
            "total_interactions": self.interactions,
        }
