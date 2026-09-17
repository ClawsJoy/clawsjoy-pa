#!/usr/bin/env python3
"""TaskEngine v8.0 — 任务状态机 + 事件驱动通知"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List


TASK_STATES = ["pending", "running", "done", "reviewed", "failed", "pending_review"]

TASK_TRANSITIONS = {
    "pending": ["running", "failed"],
    "running": ["done", "failed"],
    "done": ["reviewed", "pending_review"],
    "reviewed": ["done"],  # 审查不通过，打回重做
    "pending_review": ["running", "reviewed", "failed"],  # 等待人工复核：可返工/重新审查/标记失败
}

# 状态变更 → 通知规则。mention 用岗位名，Gateway 负责查花名册找对应人。
NOTIFY_RULES = {
    "done": {"mention": "ceo", "message": "任务完成，请审查"},
    "reviewed": {"mention": "{executor}", "message": "审查通过"},
    "failed": {"mention": "老板", "message": "任务失败"},
    "pending_review": {"mention": "老板", "message": "审查结果为空，等待人工复核"},
}
class TaskEngine:
    """任务状态机 — 管理任务生命周期，触发事件通知"""

    def __init__(self, data_dir: str = "data/v8"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._hooks = []  # 状态变更回调

    def _tasks_file(self, server_id: str) -> Path:
        return self.data_dir / f"tasks_{server_id}.json"

    def _load(self, server_id: str) -> dict:
        f = self._tasks_file(server_id)
        if f.exists():
            return json.loads(f.read_text())
        return {"tasks": {}, "next_id": 1}

    def _save(self, server_id: str, data: dict):
        self._tasks_file(server_id).write_text(
            json.dumps(data, indent=2, ensure_ascii=False)
        )

    # ========== 钩子注册 ==========

    def on_state_change(self, callback):
        """注册状态变更回调。callback(task_id, old_state, new_state, task_data)"""
        self._hooks.append(callback)

    def _trigger_hooks(self, task_id: str, old_state: str, new_state: str, task_data: dict):
        for hook in self._hooks:
            try:
                hook(task_id, old_state, new_state, task_data)
            except Exception:
                pass

    # ========== 任务 CRUD ==========

    def create(self, server_id: str, title: str, assigned_to: str,
               assigned_position: str = "", created_by: str = "老板",
               priority: str = "normal") -> dict:
        """创建任务"""
        data = self._load(server_id)
        tid = f"task_{data['next_id']:04d}"
        data["next_id"] += 1

        task = {
            "id": tid,
            "title": title,
            "status": "pending",
            "assigned_to": assigned_to,       # 员工名
            "assigned_position": assigned_position,  # 岗位名
            "created_by": created_by,
            "priority": priority,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "history": [{"state": "pending", "at": datetime.now().isoformat()}],
        }
        data["tasks"][tid] = task
        self._save(server_id, data)
        return task

    def transition(self, server_id: str, task_id: str, new_state: str,
                   comment: str = "") -> dict:
        """变更任务状态"""
        if new_state not in TASK_STATES:
            return {"success": False, "error": f"无效状态: {new_state}"}

        data = self._load(server_id)
        task = data["tasks"].get(task_id)
        if not task:
            return {"success": False, "error": f"任务不存在: {task_id}"}

        old_state = task["status"]
        allowed = TASK_TRANSITIONS.get(old_state, [])
        if new_state not in allowed:
            return {"success": False, "error": f"不允许 {old_state} → {new_state}"}

        task["status"] = new_state
        task["updated_at"] = datetime.now().isoformat()
        task["history"].append({
            "state": new_state,
            "at": datetime.now().isoformat(),
            "comment": comment,
        })
        self._save(server_id, data)
        # V9 注入：同步写入 task_progress 表
        try:
            from core.lib.code_entity_extractor import extractor
            extractor.update_task_progress(
                task_name=f'{server_id}:{task.get("title", task_id)}',
                session_id=server_id,
                step_number=hash(task_id) % 10000,
                step_description=f"V8 状态变更: {old_state} → {new_state}",
                tool_name=f"task_engine:{task.get('assigned_to', 'unknown')}",
                file_path="",
                status="completed" if new_state in ("done", "reviewed") else "in_progress",
                error_message=comment if new_state == "failed" else ""
            )
            # 同步写入 agent_actions
            extractor.insert_agent_action(
                session_id=server_id,
                task_name=task.get("title", task_id),
                tool_name=task.get("assigned_to", "task_engine"),
                result=new_state,
                file_type="task",
                agent_reaction="",
                detail=f"{old_state} → {new_state}: {comment}"
            )
        except Exception:
            pass
        self._trigger_hooks(task_id, old_state, new_state, task)
        return {"success": True, "task": task, "old_state": old_state}

    def get(self, server_id: str, task_id: str) -> Optional[dict]:
        data = self._load(server_id)
        return data["tasks"].get(task_id)

    def list(self, server_id: str, status: str = None) -> List[dict]:
        data = self._load(server_id)
        tasks = list(data["tasks"].values())
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        return sorted(tasks, key=lambda t: t["updated_at"], reverse=True)

    def list_by_agent(self, server_id: str, agent_name: str) -> List[dict]:
        data = self._load(server_id)
        return sorted(
            [t for t in data["tasks"].values() if t["assigned_to"] == agent_name],
            key=lambda t: t["updated_at"], reverse=True,
        )

    # ========== 通知规则 ==========

    def get_notification(self, new_state: str, task: dict) -> Optional[dict]:
        rule = NOTIFY_RULES.get(new_state)
        if not rule:
            return None
        mention = rule["mention"]
        if mention == "ceo":
            try:
                from core.lib.v8.roster_engine import roster_engine
                for m in roster_engine.list_active("default"):
                    if m.get("role") == "ceo" or "决策" in m.get("name", ""):
                        mention = m["name"]
                        break
            except Exception:
                pass
        mention = mention.replace("{executor}", task.get("assigned_to", ""))
        return {
            "mention": mention,
            "message": rule["message"],
            "task_id": task["id"],
            "task_title": task["title"],
        }


# ========== 全局单例 ==========
task_engine = TaskEngine()
