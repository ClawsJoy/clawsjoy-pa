#!/usr/bin/env python3
"""Monitoring Integration - Monitoring Integration 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""监控整合器 - 整合旁路监控和健康检查"""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests


class MonitoringIntegration:
    """整合旁路监控和健康检查"""

    def __init__(self):
        self.health_log = Path("logs/health_monitor.log")
        self.monitor_log = Path("logs/monitor.log")

    def get_health_status(self) -> Dict:
        """获取健康状态"""
        services = ["gateway", "file", "multi_agent", "doc_generator"]
        status = {}

        for service in services:
            try:
                if service == "gateway":
                    resp = requests.get(
                        'http://{unified_config.get("services.gateway.host", "localhost")}:{unified_config.get("services.gateway.port", 5002)}/api/health',
                        timeout=3,
                    )
                    status[service] = (
                        "healthy" if resp.status_code == 200 else "unhealthy"
                    )
                else:
                    # 其他服务可能未启动
                    status[service] = "unknown"
            except Exception as e:
                status[service] = "unhealthy"

        return status

    def get_recent_alerts(self, lines: int = 10) -> List[str]:
        """获取最近的告警"""
        alerts = []
        if self.monitor_log.exists():
            with open(self.monitor_log, "r") as f:
                all_lines = f.readlines()
                for line in all_lines[-lines:]:
                    if "⚠️" in line or "ERROR" in line or "告警" in line:
                        alerts.append(line.strip())
        return alerts

    def get_health_summary(self) -> Dict:
        """获取健康摘要"""
        status = self.get_health_status()
        healthy_count = sum(1 for s in status.values() if s == "healthy")
        total = len(status)

        return {
            "status": "healthy" if healthy_count == total else "degraded",
            "healthy_count": healthy_count,
            "total": total,
            "details": status,
            "timestamp": datetime.now().isoformat(),
        }

    def trigger_self_heal(self, issue: str) -> Dict:
        """触发自愈"""
        try:
            # 尝试调用自愈技能
            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "-X",
                    "POST",
                    'http://{unified_config.get("services.gateway.host", "localhost")}:{unified_config.get("services.gateway.port", 5002)}/api/skills/execute',
                    "-H",
                    "Content-Type: application/json",
                    "-d",
                    f'{{"skill": "self_heal", "params": {{"issue": "{issue}"}}}}',
                ],
                capture_output=True,
                text=True,
                timeout=unified_config.get("timeouts.default", 30),
            )
            return {"success": True, "result": result.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}


monitoring = MonitoringIntegration()
