#!/usr/bin/env python3
"""Task Generator - Task Generator 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""任务生成器 v1.2.0 - 基于真实热点"""

import hashlib
import random
import time
from datetime import datetime

from core.lib.hot_data_source import hot_data
from core.lib.task_queue import Priority, Task, task_queue


class TaskGenerator:
    def __init__(self):
        self.last_generate = None
        self.total_generated = 0
        self.video_count = 0
        self.query_count = 0

    def generate(self) -> int:
        new_tasks = []
        status = task_queue.get_status()

        # 1. 热点视频任务（优先级高）
        if status["pending"] < 3:
            new_tasks.append(self._create_hot_video_task())

        # 2. 记忆查询任务
        if status["pending"] < 2:
            new_tasks.append(self._create_query_task())

        # 3. 状态检查任务
        if self._need_status_check():
            new_tasks.append(self._create_status_task())

        added = 0
        for task in new_tasks:
            if task_queue.add(task):
                added += 1

        self.last_generate = datetime.now()
        self.total_generated += added
        return added

    def _create_hot_video_task(self) -> Task:
        """基于热点的视频任务"""
        topics = hot_data.get_topics(3)
        topic = topics[0]["topic"] if topics else "人工智能"
        score = topics[0]["score"] if topics else 50

        self.video_count += 1
        task_id = f"hot_video_{int(time.time())}_{self.video_count}"

        # 热度高 => 优先级高
        if score > 85:
            priority = Priority.HIGH
        elif score > 70:
            priority = Priority.NORMAL
        else:
            priority = Priority.LOW

        return Task(
            task_id=task_id,
            name=f"[热度{score}] 制作视频: {topic}",
            skill="manju_maker",
            params={"topic": topic},
            priority=priority,
            source="hot_generator",
        )

    def _create_query_task(self) -> Task:
        """记忆查询任务"""
        self.query_count += 1
        task_id = f"query_{int(time.time())}_{self.query_count}"
        return Task(
            task_id=task_id,
            name="记忆健康检查",
            skill="memory_query",
            params={"query": "system status", "n": 5},
            priority=Priority.LOW,
            source="generator",
        )

    def _need_status_check(self) -> bool:
        """是否需要状态检查（每10个任务一次）"""
        return (self.video_count + self.query_count) % 10 == 0

    def _create_status_task(self) -> Task:
        """状态检查任务"""
        task_id = f"status_{int(time.time())}"
        return Task(
            task_id=task_id,
            name="系统状态检查",
            skill="memory_enhanced",
            params={"action": "stats"},
            priority=Priority.LOW,
            source="generator",
        )


task_generator = TaskGenerator()
