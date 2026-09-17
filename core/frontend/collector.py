#!/usr/bin/env python3
"""Collector - Collector 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List

from core.lib.unified_config import unified_config


class FrontendCollector:
    """前端数据采集器 - 接收前端埋点数据"""

    VERSION = "1.0.0"

    def __init__(self):
        self.lock = Lock()
        self.metrics_dir = Path(f"{config_helper.get_data_root()}/frontend_metrics")
        self.errors_file = Path(f"{config_helper.get_data_root()}/frontend_errors.json")
        self.behavior_dir = Path(f"{config_helper.get_data_root()}/user_behavior")
        self._init_storage()
        print(f"📊 前端数据采集器 v{self.VERSION} 已启动")

    def _init_storage(self):
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.behavior_dir.mkdir(parents=True, exist_ok=True)
        if not self.errors_file.exists():
            self._save_errors([])

    def _save_errors(self, errors):
        with open(self.errors_file, "w") as f:
            json.dump(errors, f, indent=2)

    def _load_errors(self):
        if self.errors_file.exists():
            with open(self.errors_file, "r") as f:
                return json.load(f)
        return []

    def collect_page_view(
        self, page: str, user_id: str = None, metadata: Dict = None
    ) -> Dict:
        """采集页面访问"""
        with self.lock:
            metric = {
                "type": "page_view",
                "page": page,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
            }
            date = datetime.now().strftime("%Y%m%d")
            file_path = self.metrics_dir / f"metrics_{date}.json"

            existing = []
            if file_path.exists():
                with open(file_path, "r") as f:
                    existing = json.load(f)

            existing.append(metric)
            # 保留最近1000条
            existing = existing[-1000:]

            with open(file_path, "w") as f:
                json.dump(existing, f, indent=2)

            return {"success": True, "collected": "page_view"}

    def collect_error(self, error: str, stack: str = None, user_id: str = None) -> Dict:
        """采集前端错误"""
        with self.lock:
            errors = self._load_errors()
            error_record = {
                "error": error,
                "stack": stack,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
            }
            errors.append(error_record)
            # 保留最近500条
            errors = errors[-500:]
            self._save_errors(errors)
            return {"success": True, "collected": "error"}

    def collect_behavior(
        self, action: str, target: str = None, user_id: str = None
    ) -> Dict:
        """采集用户行为"""
        with self.lock:
            behavior = {
                "action": action,
                "target": target,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
            }
            date = datetime.now().strftime("%Y%m%d")
            file_path = self.behavior_dir / f"behavior_{date}.json"

            existing = []
            if file_path.exists():
                with open(file_path, "r") as f:
                    existing = json.load(f)

            existing.append(behavior)
            existing = existing[-2000:]

            with open(file_path, "w") as f:
                json.dump(existing, f, indent=2)

            return {"success": True, "collected": "behavior"}

    def get_stats(self) -> Dict:
        """获取采集统计"""
        metrics_count = len(list(self.metrics_dir.glob("*.json")))
        errors_count = len(self._load_errors())
        behavior_count = len(list(self.behavior_dir.glob("*.json")))

        return {
            "metrics_files": metrics_count,
            "errors_count": errors_count,
            "behavior_files": behavior_count,
        }


frontend_collector = FrontendCollector()
