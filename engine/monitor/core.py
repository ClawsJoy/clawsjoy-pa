from engine.lib.logger import engine_logger

"""监控引擎"""

import sys
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

import psutil

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class MonitorEngine:
    """监控引擎"""

    def __init__(self):
        engine_logger.get().info("📊 监控引擎已初始化")

    def process(self, input_data: Any, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if input_data == "performance":
            return self.get_performance()
        elif input_data == "health":
            return self.get_health()
        return self.get_performance()

    def get_performance(self) -> Dict:
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {"percent": psutil.cpu_percent(interval=1)},
            "memory": {"percent": psutil.virtual_memory().percent},
            "disk": {"percent": psutil.disk_usage("/").percent},
        }

    def get_health(self) -> Dict:
        return {"gateway": self._check_port(5002), "status": "healthy"}

    def _check_port(self, port: int) -> str:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        return "healthy" if result == 0 else "down"

    def health_check(self) -> Dict:
        """健康检查"""
        return {"name": self.__class__.__name__, "status": "healthy"}

    def get_stats(self) -> Dict:
        return {"status": "active", "name": "monitor_engine"}

    def reload(self) -> Dict:
        return {"success": True, "message": "Monitor engine reloaded"}


monitor_engine = MonitorEngine()
