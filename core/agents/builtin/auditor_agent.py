#!/usr/bin/env python3
"""Auditor Agent - Auditor Agent 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.agents.base.smart_agent import SmartAgent
from core.lib.config_helper import get_data_root


class AuditorAgent(SmartAgent):
    """审计师 - 负责核对数据进出数量"""

    name = "auditor_agent"
    description = "数据审计和异常检测"
    version = "1.0.0"

    _instance = None

    def __new__(cls, user_id: str = "system"):
        """单例模式，确保只有一个审计师实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, user_id: str = "system"):
        """初始化审计师"""
        if hasattr(self, "_initialized"):
            return
        super().__init__(user_id=user_id)
        self._initialized = True
        self._load_records()
        print(f"📋 审计师 v{self.VERSION} 已启动")

    def _load_records(self):
        """加载审计记录"""
        record_file = Path(f"{get_data_root()}/audit_records.json")
        if record_file.exists():
            try:
                with open(record_file, "r") as f:
                    self.records = json.load(f)
            except Exception:
                self._init_records()
        else:
            self._init_records()

    def _init_records(self):
        """初始化审计记录"""
        self.records = {"vector_operations": [], "daily_stats": [], "anomalies": []}

    def _save_records(self):
        """保存审计记录"""
        record_file = Path(f"{get_data_root()}/audit_records.json")
        record_file.parent.mkdir(parents=True, exist_ok=True)
        with open(record_file, "w") as f:
            json.dump(self.records, f, indent=2)

    def audit(self, operation: str, data: Dict) -> bool:
        """审计操作"""
        self.records["vector_operations"].append(
            {
                "operation": operation,
                "data": data,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self._save_records()
        return True

    def get_daily_report(self) -> Dict:
        """获取每日报告"""
        today = datetime.now().strftime("%Y-%m-%d")
        today_ops = [
            op
            for op in self.records["vector_operations"]
            if op["timestamp"].startswith(today)
        ]

        anomalies_today = [
            a for a in self.records["anomalies"] if a["timestamp"].startswith(today)
        ]

        return {
            "date": today,
            "total_operations": len(today_ops),
            "anomalies_count": len(anomalies_today),
            "anomalies": anomalies_today,
            "status": "⚠️ 有异常" if anomalies_today else "✅ 正常",
        }

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "name": self.name,
            "version": self.version,
            "total_operations": len(self.records.get("vector_operations", [])),
            "total_anomalies": len(self.records.get("anomalies", [])),
            "latest_anomaly": (
                self.records["anomalies"][-1] if self.records.get("anomalies") else None
            ),
        }
