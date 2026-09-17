#!/usr/bin/env python3
"""Thread Monitor - Thread Monitor 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import threading
import time
from typing import Dict


class ThreadMonitor:
    """线程监控器"""

    def __init__(self):
        self.threads: Dict[str, threading.Thread] = {}
        self.lock = threading.Lock()

    def register(self, name: str, thread: threading.Thread):
        with self.lock:
            self.threads[name] = thread

    def get_status(self) -> Dict:
        with self.lock:
            return {
                name: {"alive": t.is_alive(), "daemon": t.daemon, "ident": t.ident}
                for name, t in self.threads.items()
            }


thread_monitor = ThreadMonitor()
