#!/usr/bin/env python3
"""Resource Monitor - Resource Monitor 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""资源监控器 v1.0.01 - 配置驱动版"""

import time
from typing import Dict

from core.lib.config_loader import config

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class ResourceMonitor:
    VERSION = "1.0.01"

    def __init__(self):
        self.enabled = config.get("optimization.enable_resource_throttle", True)
        self.cpu_threshold = config.get("thresholds.cpu_threshold", 80)
        self.memory_threshold = config.get("thresholds.memory_threshold", 85)
        self.check_interval = config.get("resources.check_interval", 60)
        self.throttle_enabled = config.get("resources.throttle_when_high_load", True)
        self._last_check = 0
        self._last_status = None

    def get_status(self) -> Dict:
        if not PSUTIL_AVAILABLE:
            return {"healthy": True, "error": "psutil not installed"}

        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()

            healthy = (
                cpu < self.cpu_threshold and memory.percent < self.memory_threshold
            )

            status = {
                "cpu_percent": cpu,
                "memory_percent": memory.percent,
                "healthy": healthy,
                "timestamp": time.time(),
            }
            self._last_status = status
            self._last_check = time.time()
            return status
        except Exception as e:
            return {"healthy": True, "error": str(e)}

    def should_throttle(self) -> bool:
        if not self.enabled or not self.throttle_enabled:
            return False

        now = time.time()
        if now - self._last_check > self.check_interval or self._last_status is None:
            self.get_status()

        if self._last_status:
            return not self._last_status.get("healthy", True)
        return False

    def get_status_report(self) -> Dict:
        status = self.get_status()
        return {
            "version": self.VERSION,
            "enabled": self.enabled,
            "should_throttle": self.should_throttle(),
            "monitor": status,
        }


resource_monitor = ResourceMonitor()
