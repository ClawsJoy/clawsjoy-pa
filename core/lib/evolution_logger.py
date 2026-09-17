#!/usr/bin/env python3
"""Evolution Logger - Evolution Logger 模块

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

"""进化记录器 - 记录系统进化历史"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from core.lib.memory_vector import vector_memory


class EvolutionLogger:
    """进化记录器"""

    def __init__(self):
        self.log_file = Path(f"{get_data_root()}/evolution.json")
        self._load()

    def _load(self):
        if self.log_file.exists():
            with open(self.log_file, "r") as f:
                self.log = json.load(f)
        else:
            self.log = {"events": [], "stats": {"total": 0}}
        # 确保 events 字段存在
        if "events" not in self.log:
            self.log["events"] = []
        if "stats" not in self.log:
            self.log["stats"] = {"total": 0}

    def _save(self):
        with open(self.log_file, "w") as f:
            json.dump(self.log, f, indent=2)

    def log_evolution(self, event_type: str, data: Dict):
        """记录进化事件"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data,
        }
        self.log["events"].append(event)
        self.log["stats"]["total"] += 1

        # 存储到向量记忆
        try:
            vector_memory.add(
                text=f"进化事件: {event_type} | {data.get('description', '')}",
                category="evolution",
                metadata={"type": event_type},
            )
        except Exception as e:
            pass

        self._save()
        print(f"📈 进化记录: {event_type}")

    def get_history(self, limit: int = 50) -> list:
        return self.log["events"][-limit:]


evolution_logger = EvolutionLogger()
