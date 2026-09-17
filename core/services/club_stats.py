#!/usr/bin/env python3
"""Club Stats - Club Stats 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
import time
from datetime import datetime
from pathlib import Path
from threading import Thread


class ClubStatsCollector:
    """俱乐部数据收集器（脱敏）"""

    def __init__(self):
        self.stats_file = Path("data/butler_club/stats.json")
        self.members_dir = Path("data/butler_club/members")
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        self.members_dir.mkdir(parents=True, exist_ok=True)
        self._running = False

    def start(self):
        """启动数据收集"""
        self._running = True
        Thread(target=self._collect_loop, daemon=True).start()
        print("📊 俱乐部数据收集服务已启动")

    def _collect_loop(self):
        while self._running:
            time.sleep(300)  # 每5分钟收集一次
            self.collect()

    def collect(self):
        """收集脱敏数据"""
        try:
            # 统计成员数量
            members = list(self.members_dir.glob("*"))
            total_members = len(members)

            # 读取现有统计
            stats = {}
            if self.stats_file.exists():
                with open(self.stats_file, "r") as f:
                    stats = json.load(f)

            stats.update(
                {
                    "total_members": total_members,
                    "updated_at": datetime.now().isoformat(),
                    "anonymized": True,
                }
            )

            with open(self.stats_file, "w") as f:
                json.dump(stats, f, indent=2)

        except Exception as e:
            print(f"数据收集失败: {e}")

    def record_interaction(self, user_id: str, dialect_used: bool = False):
        """记录交互（脱敏）"""
        # 只记录数字统计，不记录用户标识
        pass


club_stats = ClubStatsCollector()
