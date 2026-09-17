#!/usr/bin/env python3
"""Log Aggregator - Log Aggregator 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""日志聚合器 - 集中管理所有日志"""

import json
import os
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path


class LogAggregator:
    def __init__(self, log_dir="logs"):
        self.log_dir = Path(log_dir)
        self.log_cache = defaultdict(lambda: deque(maxlen=100))
        self._load_recent()

    def _load_recent(self):
        """加载最近日志"""
        for log_file in self.log_dir.glob("*.log"):
            try:
                with open(log_file, "r") as f:
                    lines = f.readlines()[-50:]
                    self.log_cache[log_file.stem] = deque(lines, maxlen=100)
            except Exception as e:
                pass

    def get_logs(self, service=None, lines=50):
        """获取日志"""
        if service:
            return list(self.log_cache.get(service, []))[-lines:]

        all_logs = {}
        for name, logs in self.log_cache.items():
            all_logs[name] = list(logs)[-lines:]
        return all_logs

    def search_logs(self, keyword, service=None, lines=20):
        """搜索日志"""
        results = []
        targets = [service] if service else self.log_cache.keys()

        for svc in targets:
            for log in self.log_cache.get(svc, []):
                if keyword.lower() in log.lower():
                    results.append({"service": svc, "log": log.strip()})
                    if len(results) >= lines:
                        return results
        return results

    def get_errors(self, service=None, lines=20):
        """获取错误日志"""
        return self.search_logs("error", service, lines)

    def get_summary(self):
        """获取日志摘要"""
        return {
            "total_services": len(self.log_cache),
            "services": list(self.log_cache.keys()),
            "total_lines": sum(len(logs) for logs in self.log_cache.values()),
        }


log_aggregator = LogAggregator()
