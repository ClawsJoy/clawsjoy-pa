"""任务编排引擎 - 支持状态管理和回滚"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.lib.parallel_scheduler import ParallelScheduler


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLBACK = "rollback"
    ROLLED_BACK = "rolled_back"
    EXPIRED = "expired"
    BLOCKED = "blocked"


@dataclass
class SubTask:
    id: str
    name: str
    agent: str
    action: str
    params: Dict
    depends_on: List[str] = field(default_factory=list)
    rollback_action: Optional[str] = None
    rollback_params: Optional[Dict] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    checkpoint: bool = False
    optional: bool = False
    parallel_group: Optional[str] = None
    interactive: bool = False


@dataclass
class OrchestrationPlan:
    id: str
    name: str
    description: str
    tasks: List[SubTask]
    created_at: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.PENDING
    current_task: Optional[str] = None
    checkpoints: Dict[str, Any] = field(default_factory=dict)


class TaskManager:
    def __init__(self, storage_dir: str = "data/orchestration"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.active_plans: Dict[str, OrchestrationPlan] = {}
        self.scheduler = ParallelScheduler()

    def create_plan(self, name: str, description: str, tasks: List[Dict]) -> OrchestrationPlan:
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        subtasks = []
        for i, task in enumerate(tasks):
            subtasks.append(
                SubTask(
                    id=f"{plan_id}_{i}",
                    name=task.get("name"),
                    agent=task.get("agent"),
                    action=task.get("action", "handle"),
                    params=task.get("params", {}),
                    depends_on=task.get("depends_on", []),
                    rollback_action=task.get("rollback_action"),
                    rollback_params=task.get("rollback_params", {}),
                    checkpoint=task.get("checkpoint", False),
                    optional=task.get("optional", False),
                    parallel_group=task.get("parallel_group"),
                    interactive=task.get("interactive", False),
                )
            )

        plan = OrchestrationPlan(id=plan_id, name=name, description=description, tasks=subtasks)

        self.active_plans[plan_id] = plan
        self._save_plan(plan)
        return plan

    def execute_plan_parallel(self, plan_id: str, agent_getter) -> Dict:
        """按 parallel_group 分组调度：同组 ThreadPoolExecutor 并行，组间串行推进；
        执行每个子任务前做依赖链校验：depends_on 前置任务必须全部 completed，
        否则当前子任务标记为 blocked 并跳过"""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return {"success": False, "error": "计划不存在"}

        plan.status = TaskStatus.RUNNING
        results = []

        pending = [t for t in plan.tasks if t.status == TaskStatus.PENDING]
        if not pending:
            plan.status = TaskStatus.COMPLETED
            return self._format_result(plan, results, True)

        # 1. 按 parallel_group 分组（无 parallel_group 的任务各自独立成组，保持串行语义）
        groups: Dict[str, List[SubTask]] = {}
        for task in pending:
            key = task.parallel_group or "__seq__" + task.id
            groups.setdefault(key, []).append(task)

        # 2. 组间串行推进，每组执行前做依赖链校验
        for group_tasks in groups.values():
            runnable = []
            for task in group_tasks:
                if self._check_dependencies(task, plan):
                    runnable.append(task)
                else:
                    # 前置任务失败/未完成 → 当前子任务自动跳过，标记 blocked
                    task.status = TaskStatus.BLOCKED
                    results.append(self._task_outcome(task))
            if not runnable:
                continue
            if len(runnable) == 1:
                ok = self._run_single(runnable[0], agent_getter, results)
            else:
                ok = self._run_group_parallel(runnable, agent_getter, results)
            if not ok:
                return self._format_result(plan, results, False)

        plan.status = TaskStatus.COMPLETED
        return self._format_result(plan, results, True)

    def _check_dependencies(self, task: SubTask, plan: OrchestrationPlan) -> bool:
        """依赖链校验：depends_on 中的前置任务必须全部 completed。
        任一前置任务失败、未完成或不存在 → 返回 False（由调用方标记 blocked）"""
        if not task.depends_on:
            return True
        task_index = {t.id: t for t in plan.tasks}
        for dep_id in task.depends_on:
            dep = task_index.get(dep_id)
            if dep is None:
                task.error = "前置任务 {} 不存在".format(dep_id)
                return False
            if dep.status != TaskStatus.COMPLETED:
                task.error = "前置任务 {}({}) 状态为 {}，未完成，当前子任务标记为 blocked".format(dep_id, dep.name, dep.status.value)
                return False
        return True

    def _run_single(self, task: SubTask, agent_getter, results: List) -> bool:
        """串行执行单个任务；返回 False 表示非 optional 失败，应终止"""
        task, ok = self._execute_task_isolated(agent_getter, task)
        results.append(self._task_outcome(task))
        return ok

    def _run_group_parallel(self, group_tasks: List[SubTask], agent_getter, results: List) -> bool:
        """同组任务 ThreadPoolExecutor 并行执行；子任务失败时自动重试最多 2 次（间隔 5 秒）；
        重试仍失败则标记 failed，继续执行其他子任务；
        返回 False 表示组内存在非 optional 失败"""
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        all_ok = True
        max_workers = min(len(group_tasks), 5)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {}
            for task in group_tasks:
                if task.status == TaskStatus.PENDING:
                    future_map[executor.submit(self._execute_task_isolated, agent_getter, task)] = task
                    time.sleep(2)
            for future in as_completed(future_map):
                task = future_map[future]
                try:
                    _, ok = future.result(timeout=1800)
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    ok = False
                # 失败重试：ok=False 时自动重试最多 2 次，每次间隔 5 秒
                for _ in range(2):
                    if ok:
                        break
                    time.sleep(5)
                    task, ok = self._execute_task_isolated(agent_getter, task)
                if not ok:
                    task.status = TaskStatus.FAILED
                    all_ok = False
                results.append(self._task_outcome(task))
        return all_ok

    def _execute_task_isolated(self, agent_getter, task: SubTask):
        """线程隔离执行：获取 Agent 并执行任务，返回 (task, ok)"""
        agent = agent_getter(task.agent)
        if not agent:
            task.status = TaskStatus.FAILED
            task.error = "Agent {} 不可用".format(task.agent)
            return task, task.optional
        result = self._execute_task(agent, task)
        task.status = result.status
        task.result = result.result
        task.error = result.error
        ok = task.status == TaskStatus.COMPLETED or task.optional
        return task, ok

    def _record_subtask_feedback(self, task: SubTask):
        """子任务自学习反馈：结果写入 SAG code_entities（entity_type=subtask_result），
        供过滤网/拆解器后续检索复用，失败不阻塞主流程"""
        try:
            from core.lib.code_entity_extractor import extractor

            extractor.upsert_entity(
                {
                    "entity_type": "subtask_result",
                    "entity_name": f"subtask::{task.id}",
                    "file_path": "engine/orchestration/task_manager.py",
                    "signature": json.dumps(
                        {
                            "name": task.name,
                            "agent": task.agent,
                            "action": task.action,
                            "status": task.status.value,
                            "result": (task.result.get("response", "")[:200] if task.result else ""),
                            "error": task.error,
                            "timestamp": datetime.now().isoformat(),
                        },
                        ensure_ascii=False,
                    ),
                    "related_entities": [task.agent] if task.agent else [],
                }
            )
        except Exception as e:
            print(f"[SUBTASK_FEEDBACK] {task.id} 自学习入库失败: {e}")

    def _task_outcome(self, task: SubTask) -> Dict:
        """构造单任务执行结果记录"""
        self._record_subtask_feedback(task)
        return {
            "task": task.name,
            "success": task.status == TaskStatus.COMPLETED,
            "response": (task.result.get("response", "")[:200] if task.result else task.error),
        }

    def _execute_task(self, agent, task: SubTask) -> SubTask:
        if not hasattr(agent, "handle"):
            task.status = TaskStatus.FAILED
            task.error = f"Agent {task.agent} 没有 handle 方法"
            return task

        method = getattr(agent, "handle")
        message = task.params.get("message", "")

        write_paths = task.params.get("write_files") or []
        try:
            with self.scheduler.write_locks(write_paths):
                result = method(message, None)
            task.status = TaskStatus.COMPLETED
            task.result = result
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)

        return task

    def _format_result(self, plan: OrchestrationPlan, results: List, success: bool) -> Dict:
        return {
            "success": success,
            "plan_id": plan.id,
            "total_tasks": len(plan.tasks),
            "completed": len([t for t in plan.tasks if t.status == TaskStatus.COMPLETED]),
            "failed": len([t for t in plan.tasks if t.status == TaskStatus.FAILED]),
            "results": results,
        }

    def _save_plan(self, plan: OrchestrationPlan):
        import json

        plan_data = {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "created_at": plan.created_at.isoformat(),
            "status": plan.status.value,
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "agent": t.agent,
                    "status": t.status.value,
                    "result": t.result,
                    "error": t.error,
                }
                for t in plan.tasks
            ],
        }
        with open(self.storage_dir / f"{plan.id}.json", "w", encoding="utf-8") as f:
            json.dump(plan_data, f, indent=2, ensure_ascii=False)

    def get_plan_status(self, plan_id: str) -> Dict:
        plan = self.active_plans.get(plan_id)
        if not plan:
            return {"success": False, "error": "计划不存在"}

        return {
            "success": True,
            "plan_id": plan.id,
            "name": plan.name,
            "status": plan.status.value,
            "progress": f"{len([t for t in plan.tasks if t.status == TaskStatus.COMPLETED])}/{len(plan.tasks)}",
            "tasks": [{"name": t.name, "status": t.status.value, "error": t.error} for t in plan.tasks],
        }

    @classmethod
    def register_tasks_from_json(cls, json_path: str):
        """从 tasks.json 读取任务定义并入库 SAG"""
        import json

        try:
            from core.lib.code_entity_extractor import extractor

            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            tasks = data if isinstance(data, list) else data.get("tasks", [])
            count = 0
            for task in tasks:
                task_id = task.get("id") or task.get("name", "unknown")
                extractor.upsert_entity(
                    {
                        "entity_type": "task",
                        "entity_name": f"task::{task_id}",
                        "file_path": json_path,
                        "signature": json.dumps(task, ensure_ascii=False),
                        "related_entities": task.get("related", []),
                    }
                )
                count += 1
            print(f"[REGISTRY] {json_path} → {count} 条 task 定义已入库")
            return count
        except Exception as e:
            print(f"[REGISTRY] {json_path} 入库失败: {e}")
            return 0


task_manager = TaskManager()
