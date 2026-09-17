#!/usr/bin/env python3
"""File Exchange - File Exchange 模块

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

"""异步文件夹交割通信 - 配置驱动路径"""
import json
import shutil
import threading
import time
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from core.lib.path_manager import path_manager


class MessagePriority(Enum):
    HIGH = 0
    NORMAL = 1
    LOW = 2


class FileExchange:
    def __init__(self, exchange_dir: str = None):
        if exchange_dir is None:
            exchange_dir = str(Path(f"{get_data_root()}/exchange"))
        self.exchange_dir = Path(exchange_dir)
        self._init_dirs()
        self.handlers: Dict[str, Callable] = {}
        self._listener_thread = None
        self._running = False

    def _init_dirs(self):
        self.dirs = {
            "incoming": self.exchange_dir / "incoming",
            "to_decision": self.exchange_dir / "to_decision",
            "to_chat": self.exchange_dir / "to_chat",
            "to_executor": self.exchange_dir / "to_executor",
            "processing": self.exchange_dir / "processing",
            "done": self.exchange_dir / "done",
            "urgent": self.exchange_dir / "urgent",
        }
        for d in self.dirs.values():
            d.mkdir(parents=True, exist_ok=True)

    def send(
        self,
        to_agent: str,
        data: Dict,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> str:
        message_id = (
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.json"
        )
        target_dir = self.dirs.get(f"to_{to_agent}", self.dirs["incoming"])
        file_path = target_dir / message_id
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        return message_id

    def receive(self, from_agent: str) -> Optional[Dict]:
        source_dir = self.dirs.get(f"to_{from_agent}", self.dirs["incoming"])
        for file_path in source_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                shutil.move(
                    str(file_path), str(self.dirs["processing"] / file_path.name)
                )
                return data
            except Exception as e:
                continue
        return None


file_exchange = FileExchange()
