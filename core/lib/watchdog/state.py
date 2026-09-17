"""Watchdog 状态管理"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


@dataclass
class WatchdogState:
    status: HealthStatus = HealthStatus.HEALTHY
    last_check: datetime = None
    consecutive_failures: int = 0
    last_alert: datetime = None
    suppressed_until: datetime = None
    total_checks: int = 0
    total_failures: int = 0
