#!/usr/bin/env python3
"""Tracer - Tracer 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
import time
from datetime import datetime
from functools import wraps
from pathlib import Path


class CallTracer:
    """调用追踪器"""

    def __init__(self):
        self.traces = []
        self.enabled = True

    def trace(self, name: str):
        """追踪装饰器"""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)

                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    success = True
                    error = None
                except Exception as e:
                    result = None
                    success = False
                    error = str(e)

                elapsed = time.time() - start

                self.traces.append(
                    {
                        "name": name,
                        "timestamp": datetime.now().isoformat(),
                        "duration_ms": elapsed * 1000,
                        "success": success,
                        "error": error,
                    }
                )

                # 保留最近1000条
                if len(self.traces) > 1000:
                    self.traces = self.traces[-1000:]

                return result

            return wrapper

        return decorator

    def get_stats(self) -> dict:
        """获取统计"""
        if not self.traces:
            return {"total": 0}

        total = len(self.traces)
        success = sum(1 for t in self.traces if t["success"])
        avg_duration = sum(t["duration_ms"] for t in self.traces) / total

        return {
            "total": total,
            "success_rate": success / total * 100,
            "avg_duration_ms": avg_duration,
        }

    def export(self) -> list:
        """导出追踪数据"""
        return self.traces


tracer = CallTracer()
