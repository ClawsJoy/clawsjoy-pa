#!/usr/bin/env python3
"""Rollback Manager - Rollback Manager 模块

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

"""回滚管理器"""
import json
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class RollbackManager:
    """回滚管理器"""

    def __init__(self):
        self.rollback_file = Path(f"{get_data_root()}/rollback_points.json")
        self._load_rollback_points()

    def _load_rollback_points(self):
        if self.rollback_file.exists():
            with open(self.rollback_file, "r") as f:
                self.rollback_points = json.load(f)
        else:
            self.rollback_points = {"points": []}

    def _save(self):
        with open(self.rollback_file, "w") as f:
            json.dump(self.rollback_points, f, indent=2)

    def create_point(self, action: str, before_state: Dict) -> str:
        """创建回滚点"""
        point_id = f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.rollback_points["points"].append(
            {
                "id": point_id,
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "before_state": before_state,
            }
        )
        self._save()
        return point_id

    def rollback(self, point_id: str) -> Dict:
        """回滚到指定点"""
        for point in self.rollback_points["points"]:
            if point["id"] == point_id:
                return {
                    "success": True,
                    "rolled_back": True,
                    "point": point,
                    "message": f"已回滚到 {point['timestamp']}",
                }
        return {"success": False, "message": "回滚点不存在"}

    def get_last_point(self) -> Optional[Dict]:
        """获取最后一个回滚点"""
        if self.rollback_points["points"]:
            return self.rollback_points["points"][-1]
        return None


rollback_manager = RollbackManager()
