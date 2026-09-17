#!/usr/bin/env python3
"""ProgressManager — 统一 checkpoint 结构，协调 TaskStateMachine + ContextManager + RollbackManager"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ProgressManager:
    """长时间任务的中断恢复管理器"""

    def __init__(self, user_id: str = "default", session_id: str = "default"):
        self.user_id = user_id
        self.session_id = session_id
        self.checkpoint_dir = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev")
        self.checkpoint_file = self.checkpoint_dir / ".progress_checkpoint.json"

    def save_checkpoint(
        self,
        task_name: str,
        completed_steps: List[int],
        current_step: int,
        files_modified: List[str],
        context_summary: str = "",
        pending_decisions: List[str] = None,
    ) -> bool:
        """持久化当前进度"""
        try:
            checkpoint = {
                "task_name": task_name,
                "completed_steps": completed_steps,
                "current_step": current_step,
                "files_modified": files_modified,
                "context_summary": context_summary,
                "pending_decisions": pending_decisions or [],
                "saved_at": datetime.now().isoformat(),
            }
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            self.checkpoint_file.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2))
            # 同步写入 task_progress 表
            try:
                from core.lib.code_entity_extractor import extractor
                for step in completed_steps:
                    extractor.update_task_progress(
                        task_name=task_name,
                        session_id=self.session_id,
                        step_number=step,
                        step_description=f"checkpoint 保存",
                        tool_name="progress_manager",
                        file_path="",
                        status="completed",
                    )
            except Exception:
                pass
            return True
        except Exception as e:
            print(f"[ProgressManager] 保存 checkpoint 失败: {e}")
            return False

    def load_checkpoint(self, task_name: str) -> Optional[Dict]:
        """加载最后保存的进度"""
        try:
            if not self.checkpoint_file.exists():
                return None
            checkpoint = json.loads(self.checkpoint_file.read_text())
            if checkpoint.get("task_name") == task_name:
                return checkpoint
            # task_name 不匹配，可能是旧任务的残留
            return None
        except Exception:
            return None

    def resume(self, task_name: str) -> Dict:
        """从 checkpoint 恢复，返回恢复提示"""
        checkpoint = self.load_checkpoint(task_name)
        if not checkpoint:
            return {
                "resumed": False,
                "message": "无 checkpoint 可恢复，从头开始执行。",
            }

        completed = checkpoint.get("completed_steps", [])
        current = checkpoint.get("current_step", 1)
        files = checkpoint.get("files_modified", [])
        summary = checkpoint.get("context_summary", "")

        return {
            "resumed": True,
            "completed_steps": completed,
            "current_step": current,
            "files_modified": files,
            "context_summary": summary,
            "message": (
                f"[系统] 已从 checkpoint 恢复。任务：{task_name}，"
                f"已完成 {len(completed)} 个步骤，"
                f"当前从步骤 {current} 继续。"
                f"已修改文件：{', '.join(files) if files else '无'}。"
                f"{summary if summary else ''}"
            ),
        }

    def clear_checkpoint(self) -> bool:
        """任务完成后清除 checkpoint"""
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
            return True
        except Exception:
            return False
