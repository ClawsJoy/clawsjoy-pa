# -*- coding: utf-8 -*-
"""并行调度器：多任务并发写文件的锁管理。

设计要点：
1. 每个文件路径对应一把独立的 threading.Lock，通过 _locks 字典缓存；
2. 获取写锁时对路径列表排序后逐一加锁，避免多任务交叉加锁造成死锁；
3. 释放锁按相反顺序，保证对称性。
"""

from __future__ import annotations

import threading
from typing import Dict, Iterable, List


class ParallelScheduler:
    """基于文件路径排序加锁的并行写调度器。"""

    def __init__(self) -> None:
        # 文件锁字典：path -> threading.Lock
        self._locks: Dict[str, threading.Lock] = {}
        # 保护 _locks 字典本身的并发访问
        self._locks_guard = threading.Lock()

    def get_lock(self, path: str) -> threading.Lock:
        """返回指定路径对应的锁，不存在则创建（线程安全）。"""
        with self._locks_guard:
            lock = self._locks.get(path)
            if lock is None:
                lock = threading.Lock()
                self._locks[path] = lock
            return lock

    def acquire_write_lock(self, paths: Iterable[str]) -> List[str]:
        """按路径排序后依次获取写锁，避免死锁。

        参数：
            paths: 需要加锁的文件路径集合（可迭代）。

        返回：
            已按排序顺序成功加锁的路径列表（供 release_write_lock 使用）。
        """
        ordered = sorted(set(paths))
        acquired: List[str] = []
        for path in ordered:
            self.get_lock(path).acquire()
            acquired.append(path)
        return acquired

    def release_write_lock(self, paths: Iterable[str]) -> None:
        """按逆序释放写锁（与加锁顺序对称）。

        参数：
            paths: 待释放锁的路径集合（内部会按排序逆序释放）。
        """
        for path in sorted(set(paths), reverse=True):
            lock = self._locks.get(path)
            if lock is not None and lock.locked():
                lock.release()

    # ---------- 便捷上下文管理器 ----------
    def write_locks(self, paths: Iterable[str]):
        """上下文管理器：with scheduler.write_locks([...]) 进入加锁区域。"""
        return _WriteLockScope(self, paths)


class _WriteLockScope:
    """ParallelScheduler.write_locks 的上下文管理器实现。"""

    def __init__(self, scheduler: ParallelScheduler, paths: Iterable[str]) -> None:
        self._scheduler = scheduler
        self._paths = list(paths)
        self._acquired: List[str] = []

    def __enter__(self) -> List[str]:
        self._acquired = self._scheduler.acquire_write_lock(self._paths)
        return self._acquired

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self._scheduler.release_write_lock(self._acquired)
        return False  # 不吞异常
