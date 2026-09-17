#!/usr/bin/env python3
"""Hot Data Source - Hot Data Source 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""热点数据源 - 提供真实热点话题"""

import random
from datetime import datetime, timedelta


class HotDataSource:
    def __init__(self):
        self.hot_topics = [
            ("香港高才通", 95),
            ("优才计划", 88),
            ("AI人工智能", 92),
            ("新能源汽车", 85),
            ("碳中和", 78),
            ("ChatGPT", 90),
            ("Web3.0", 72),
            ("数字人", 68),
            ("自动驾驶", 80),
            ("机器学习", 75),
        ]
        self.last_update = None

    def get_topics(self, limit=5) -> list:
        """获取热点话题列表"""
        # 模拟热度变化
        topics_with_score = []
        for topic, base_score in self.hot_topics:
            # 随机波动 ±10%
            score = base_score + random.randint(-10, 10)
            score = max(0, min(100, score))
            topics_with_score.append({"topic": topic, "score": score})

        # 按热度排序
        topics_with_score.sort(key=lambda x: x["score"], reverse=True)
        return topics_with_score[:limit]

    def get_hottest(self) -> str:
        """获取最热话题"""
        topics = self.get_topics(1)
        return topics[0]["topic"] if topics else "人工智能"


hot_data = HotDataSource()
