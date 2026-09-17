"""Watchdog 检测器"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any
import subprocess


class Checker(ABC):
    """检测器基类"""

    @abstractmethod
    def check(self) -> Dict[str, Any]:
        pass

    @property
    @abstractmethod
    def cost(self) -> str:
        pass


class FileMtimeChecker(Checker):
    """文件修改时间检测器 - 低成本"""

    cost = "low"

    def __init__(self, path: str):
        self.path = Path(path)
        self._last_mtime = None

    def check(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"changed": False, "exists": False}

        current = self.path.stat().st_mtime
        changed = self._last_mtime is not None and current != self._last_mtime
        self._last_mtime = current

        return {"changed": changed, "exists": True, "mtime": current}


class ProcessChecker(Checker):
    """进程检测器 - 低成本"""

    cost = "low"

    def __init__(self, process_name: str):
        self.process_name = process_name

    def check(self) -> Dict[str, Any]:
        result = subprocess.run(
            ["pgrep", "-f", self.process_name],
            capture_output=True
        )
        return {"running": result.returncode == 0, "name": self.process_name}
