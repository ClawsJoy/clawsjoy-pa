from core.lib.config_helper import get_data_root
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""Auditor - Auditor 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional


class SecurityAuditor:
    """安全审计员 - 最高安全防线"""

    VERSION = "1.0.0"

    def __init__(self):
        self.audit_log = Path(
            f"{unified_config.get("paths.data_root", "data")}/audit.log"
        )
        self.risk_rules = self._load_rules()
        self.risk_scores = defaultdict(int)
        self.lock = Lock()
        print(f"🔒 安全审计员 v{self.VERSION} 已启动")

    def _load_rules(self) -> Dict:
        """加载风险规则"""
        return {
            "high_frequency": {"threshold": 100, "window": 60, "risk": 50},
            "sensitive_access": {
                "keywords": ["password", "token", "secret"],
                "risk": 80,
            },
            "unauthorized": {"risk": 90},
            "anomaly_pattern": {"risk": 60},
        }

    def audit(self, action: str, actor: str, resource: str, data: Dict = None) -> Dict:
        """审计操作"""
        with self.lock:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "actor": actor,
                "resource": resource,
                "data": data,
                "risk_score": self._calculate_risk(action, actor, resource, data),
            }

            # 写入审计日志
            with open(self.audit_log, "a") as f:
                f.write(json.dumps(entry) + "\n")

            # 更新风险评分
            self.risk_scores[actor] += entry["risk_score"]

            # 高风险告警
            if entry["risk_score"] > 70:
                self._alert(entry)

            return entry

    def _calculate_risk(
        self, action: str, actor: str, resource: str, data: Dict
    ) -> int:
        """计算风险分数 (0-100)"""
        risk = 0

        # 1. 敏感操作
        if "delete" in action or "drop" in action:
            risk += 60
        if "config" in resource or "secret" in resource:
            risk += 40

        # 2. 敏感数据
        if data:
            for keyword in ["password", "token", "secret"]:
                if keyword in str(data).lower():
                    risk += 50
                    break

        # 3. 频率风险
        actions_in_window = len(
            [e for e in self._get_recent_actions(actor) if e["action"] == action]
        )
        if actions_in_window > 10:
            risk += 30

        return min(risk, 100)

    def _get_recent_actions(self, actor: str) -> List:
        """获取最近操作"""
        recent = []
        try:
            with open(self.audit_log, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    if entry["actor"] == actor:
                        recent.append(entry)
        except Exception as e:
            pass
        return recent[-100:]

    def _alert(self, entry: Dict):
        """高风险告警"""
        print(
            f"🚨 [安全告警] 高风险操作: {entry['action']} by {entry['actor']} (风险: {entry['risk_score']})"
        )
        # 可发送通知

    def get_audit_trail(self, actor: str = None) -> List:
        """获取审计轨迹"""
        trail = []
        try:
            with open(self.audit_log, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    if not actor or entry["actor"] == actor:
                        trail.append(entry)
        except Exception as e:
            pass
        return trail[-100:]

    def get_risk_summary(self) -> Dict:
        """获取风险摘要"""
        return {
            "total_entries": len(self.get_audit_trail()),
            "risk_scores": dict(self.risk_scores),
            "high_risk_actors": [a for a, s in self.risk_scores.items() if s > 200],
        }


security_auditor = SecurityAuditor()
