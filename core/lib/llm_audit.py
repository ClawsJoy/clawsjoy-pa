#!/usr/bin/env python3
"""Llm Audit - Llm Audit 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""LLM 调用审计日志 - 记录所有 LLM 交互"""

import json
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional


class LLMAudit:
    """LLM 调用审计"""

    def __init__(self):
        self.log_dir = Path("logs/llm_audit")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_log = self.log_dir / f"llm_{datetime.now().strftime('%Y%m%d')}.log"

    def log_call(self, context: Dict) -> str:
        """记录 LLM 调用"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "call_id": f"llm_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "user_id": context.get("user_id", "anonymous"),
            "agent_id": context.get("agent_id", "unknown"),
            "prompt_preview": context.get("prompt", "")[:200],
            "response_preview": context.get("response", "")[:200],
            "duration_ms": context.get("duration_ms", 0),
            "model": context.get("model", "unknown"),
            "success": context.get("success", False),
            "tokens": context.get("tokens", {}),
        }

        with open(self.current_log, "a") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        return log_entry["call_id"]

    def get_stats(self, date: str = None) -> Dict:
        """获取统计信息"""
        if date:
            log_file = self.log_dir / f"llm_{date}.log"
        else:
            log_file = self.current_log

        if not log_file.exists():
            return {"total_calls": 0}

        calls = []
        with open(log_file, "r") as f:
            for line in f:
                try:
                    calls.append(json.loads(line))
                except Exception as e:
                    pass

        total = len(calls)
        success = sum(1 for c in calls if c.get("success"))
        avg_duration = (
            sum(c.get("duration_ms", 0) for c in calls) / total if total else 0
        )

        return {
            "total_calls": total,
            "success_rate": success / total if total else 0,
            "avg_duration_ms": avg_duration,
            "by_agent": self._group_by(calls, "agent_id"),
            "by_model": self._group_by(calls, "model"),
        }

    def _group_by(self, calls: list, key: str) -> Dict:
        result = {}
        for c in calls:
            k = c.get(key, "unknown")
            result[k] = result.get(k, 0) + 1
        return result


llm_audit = LLMAudit()
