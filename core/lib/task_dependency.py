#!/usr/bin/env python3
"""Task Dependency - Task Dependency 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""任务依赖管理器 - 管理任务间先后顺序"""

from typing import Dict, List, Optional

from core.lib.task_queue import Priority, Task, task_queue


class TaskDependency:
    def __init__(self):
        self.dependencies: Dict[str, List[str]] = {}  # task_id -> [依赖的task_id]
        self.reverse: Dict[str, List[str]] = {}  # 被依赖关系

    def add_dependency(self, task_id: str, depends_on: str):
        """添加依赖关系: task_id 依赖 depends_on"""
        if task_id not in self.dependencies:
            self.dependencies[task_id] = []
        self.dependencies[task_id].append(depends_on)

        if depends_on not in self.reverse:
            self.reverse[depends_on] = []
        self.reverse[depends_on].append(task_id)

    def can_execute(self, task_id: str, completed_ids: set) -> bool:
        """检查任务是否可以执行"""
        if task_id not in self.dependencies:
            return True
        for dep_id in self.dependencies[task_id]:
            if dep_id not in completed_ids:
                return False
        return True

    def get_blocked_tasks(self, completed_ids: set) -> List[str]:
        """获取被阻塞的任务列表"""
        blocked = []
        for task_id in task_queue.pending:
            if not self.can_execute(task_id, completed_ids):
                blocked.append(task_id)
        return blocked


task_dependency = TaskDependency()
