#!/usr/bin/env python3
"""Butler Memory - Butler Memory 模块

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

"""私人管家独立记忆系统 - 配置驱动"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import chromadb

from core.lib.unified_config import unified_config


class ButlerMemory:
    def __init__(self, user_id: str):
        self.user_id = user_id
        base_path = unified_config.get(
            "butler.paths.user_data",
            unified_config.get("paths.users_dir", f"{get_data_root()}/users/") + "/{user_id}/butler_v2",
        )
        self.user_dir = Path(base_path.format(user_id=user_id))
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.user_dir / "memory.json"
        self.data = self._load_memory()

        vector_dir = self.user_dir / unified_config.get("butler.paths.vectors_dir", "vectors")
        vector_dir.mkdir(exist_ok=True)
        from chromadb.config import Settings

        self.vector_client = chromadb.PersistentClient(
            path=str(vector_dir), settings=Settings(anonymized_telemetry=False)
        )
        self.vector_collection = self.vector_client.get_or_create_collection("butler_memory")

    # ... 其余代码保持不变
