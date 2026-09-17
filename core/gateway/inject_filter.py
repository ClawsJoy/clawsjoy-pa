"""网关注入过滤器 — 在 Agent 接收请求前，自动注入关联的任务上下文"""

import logging
import json
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class InjectFilter:
    """网关注入过滤器

    在 Agent 接收请求前，自动注入关联的任务上下文（planned/confirmed 状态的任务信息），
    支持按状态过滤注入。
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def inject_task_context(
        self,
        plan_id: Optional[str] = None,
        status_filter: Optional[List[str]] = None,
        max_tasks: int = 10,
    ) -> Dict[str, Any]:
        """注入关联的任务上下文

        Args:
            plan_id: 计划 ID，为 None 时自动检测活跃计划
            status_filter: 状态过滤列表，如 ["planned", "confirmed"]，为 None 时不过滤
            max_tasks: 最大任务数

        Returns:
            包含任务上下文的字典
        """
        from engine.orchestration.task_manager import task_manager

        context = {
            "injected_tasks": [],
            "injected_plan_id": None,
            "injected_status_filter": status_filter,
        }

        # 如果指定了 plan_id，直接获取
        if plan_id:
            plan_status = task_manager.get_plan_status(plan_id)
            if plan_status.get("success"):
                context["injected_plan_id"] = plan_id
                tasks = plan_status.get("tasks", [])
                context["injected_tasks"] = self._filter_tasks(
                    tasks, status_filter, max_tasks
                )
            return context

        # 自动检测：遍历所有活跃计划
        for pid, plan in task_manager.active_plans.items():
            plan_status = task_manager.get_plan_status(pid)
            if plan_status.get("success"):
                tasks = plan_status.get("tasks", [])
                filtered = self._filter_tasks(tasks, status_filter, max_tasks)
                if filtered:
                    context["injected_plan_id"] = pid
                    context["injected_tasks"] = filtered
                    break

        return context

    def _filter_tasks(
        self,
        tasks: List[Dict],
        status_filter: Optional[List[str]],
        max_tasks: int,
    ) -> List[Dict]:
        """按状态过滤任务列表"""
        if not status_filter:
            return tasks[:max_tasks]
        filtered = [t for t in tasks if t.get("status") in status_filter]
        return filtered[:max_tasks]

    def format_injection_prompt(self, context: Dict[str, Any]) -> str:
        """将任务上下文格式化为注入提示"""
        if not context.get("injected_tasks"):
            return ""

        lines = ["[系统注入] 当前关联的任务上下文："]
        lines.append(f"  计划 ID: {context.get('injected_plan_id', 'N/A')}")

        if context.get("injected_status_filter"):
            lines.append(f"  状态过滤: {', '.join(context['injected_status_filter'])}")

        lines.append("  任务列表:")
        for i, task in enumerate(context["injected_tasks"]):
            lines.append(f"    {i+1}. [{task.get('status', '?')}] {task.get('name', '?')}")
            if task.get("error"):
                lines.append(f"       错误: {task['error']}")
            if task.get("skip_reason"):
                lines.append(f"       跳过原因: {task['skip_reason']}")
            if task.get("steps"):
                steps_str = "; ".join(f"{k}={v}" for k, v in task.get("steps", {}).items())
                if steps_str:
                    lines.append(f"       步骤: {steps_str}")

        return "\n".join(lines)


# 全局单例
inject_filter = InjectFilter()
