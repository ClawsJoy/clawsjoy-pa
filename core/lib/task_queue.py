#!/usr/bin/env python3
"""异步任务队列"""

import logging
import queue
import threading
from functools import wraps
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)


class TaskQueue:
    """简单异步任务队列"""

    def __init__(self, max_workers: int = 4):
        self._queue = queue.Queue()
        self._workers = []
        self._running = True

        for i in range(max_workers):
            worker = threading.Thread(target=self._worker, name=f"worker-{i}")
            worker.daemon = True
            worker.start()
            self._workers.append(worker)
        logger.info(f"TaskQueue initialized with {max_workers} workers")

    def _worker(self):
        """工作线程"""
        while self._running:
            try:
                task = self._queue.get(timeout=1)
                if task is None:
                    continue
                func, args, kwargs, callback = task
                try:
                    result = func(*args, **kwargs)
                    if callback:
                        callback(result)
                except Exception as e:
                    logger.error(f"Task failed: {e}")
            except queue.Empty:
                continue

    def submit(self, func: Callable, *args, callback: Callable = None, **kwargs):
        """提交异步任务"""
        self._queue.put((func, args, kwargs, callback))

    def shutdown(self):
        """关闭队列"""
        self._running = False
        for worker in self._workers:
            worker.join(timeout=2)


# 全局任务队列
task_queue = TaskQueue(max_workers=2)
