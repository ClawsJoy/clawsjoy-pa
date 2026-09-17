"""BriefManager - 任务说明书机制：跨会话/断点恢复的唯一权威任务上下文载体"""

import json, os, time
from pathlib import Path
from datetime import datetime

class BriefManager:
    def __init__(self, user_id, session_id):
        self.user_id = user_id
        self.session_id = session_id
        self.base = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev")
        self.brief_path = self.base / "BRIEF.md"
        self.plans_path = Path(f"data/plans/{session_id}")
        self.plans_path.mkdir(parents=True, exist_ok=True)
        self.master_brief = self.plans_path / "BRIEF.md"
    
    def generate(self, task_msg, done_when=""):
        meta = {
            "kind": "brief", "schema_version": "1.0",
            "task_id": f"task_{int(time.time())}",
            "session_id": self.session_id, "user_id": self.user_id,
            "status": "running", "created_at": datetime.now().isoformat(),
            "total_steps": 0, "completed_steps": 0
        }
        content = f"""---
kind: brief
task_id: {meta['task_id']}
session_id: {self.session_id}
status: running
created_at: {meta['created_at']}
---

# 任务说明书

## 1. 任务目标
> {task_msg}

## 2. 交付物定义
- 验收标准: {done_when or '写入→语法→导入→运行→内容核验'}

## 3. 执行进度
- 当前步骤: 步骤1（等待中）
"""
        self._write(content)
        return meta['task_id']
    
    def update_progress(self, step, status, summary=""):
        """读取 BRIEF.md，更新"执行进度"段（步骤状态 done/in_progress/paused），
        更新时间戳，写回 BRIEF.md（主副本 data/plans + 沙箱副本 data/projects）"""
        brief = self.load()
        if not brief:
            return
        now = datetime.now().isoformat(timespec="seconds")
        if status not in ("done", "in_progress", "paused"):
            status = "in_progress"
        lines, in_progress, progress_done = [], False, False
        for line in brief.splitlines():
            if line.strip().startswith("## 3. 执行进度"):
                in_progress = True
                lines.append(line)
                lines.append(f"- 当前步骤: {step}")
                lines.append(f"- 步骤状态: {status}")
                if summary:
                    lines.append(f"- 步骤摘要: {summary}")
                lines.append(f"- 更新时间: {now}")
                progress_done = True
                continue
            if in_progress:
                if line.startswith("## "):
                    in_progress = False
                else:
                    continue  # 跳过旧进度行，仅保留新进度
            lines.append(line)
        if not progress_done:
            lines.extend(["", "## 3. 执行进度",
                          f"- 当前步骤: {step}",
                          f"- 步骤状态: {status}"])
            if summary:
                lines.append(f"- 步骤摘要: {summary}")
            lines.append(f"- 更新时间: {now}")
        self._write("\n".join(lines) + "\n")
    
    def load(self):
        paths = [self.master_brief, self.brief_path]
        for p in paths:
            if p.exists():
                return p.read_text(encoding="utf-8")
        return None
    
    def inject(self, max_chars=3000):
        brief = self.load()
        if not brief: return ""
        return brief[:max_chars]
    
    def _write(self, content):
        for p in [self.master_brief, self.brief_path]:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")

brief_manager = None

def get_brief_manager(user_id, session_id):
    global brief_manager
    if brief_manager is None or brief_manager.session_id != session_id:
        brief_manager = BriefManager(user_id, session_id)
    return brief_manager
