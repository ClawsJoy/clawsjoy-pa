#!/usr/bin/env python3
"""Resource Monitor V1 0 00 20260517 - Resource Monitor V1 0 00 20260517 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""资源监控器 v1.0.00"""

import os
from typing import Dict

import psutil


class ResourceMonitor:
    """系统资源监控"""

    VERSION = "1.0.00"

    def __init__(self):
        self.thresholds = {"cpu_percent": 80, "memory_percent": 85, "disk_percent": 90}

    def get_status(self) -> Dict:
        """获取当前资源状态"""
        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "cpu_percent": cpu,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "healthy": cpu < self.thresholds["cpu_percent"]
                and memory.percent < self.thresholds["memory_percent"]
                and disk.percent < self.thresholds["disk_percent"],
            }
        except Exception as e:
            return {"healthy": True, "error": str(e)}

    def should_throttle(self) -> bool:
        """是否应该限流"""
        status = self.get_status()
        return not status.get("healthy", True)


resource_monitor = ResourceMonitor()
