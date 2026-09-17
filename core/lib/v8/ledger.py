#!/usr/bin/env python3
"""Ledger v8.0 — 记账 + 记事引擎"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional


class Ledger:
    """本地账本：记花费、记事件"""

    def __init__(self, data_dir: str = "data/v8"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ========== 记账 ==========

    def _billing_file(self, server_id: str) -> Path:
        return self.data_dir / f"billing_{server_id}.jsonl"

    def record_cost(self, server_id: str, agent_name: str, position: str,
                    model: str, tokens: int, unit_price: float,
                    task_id: str = "", summary: str = "") -> dict:
        """记录一次花费"""
        cost = (tokens / 1000) * unit_price
        entry = {
            "timestamp": datetime.now().isoformat(),
            "server_id": server_id,
            "agent": agent_name,
            "position": position,
            "model": model,
            "tokens": tokens,
            "unit_price": unit_price,
            "cost": round(cost, 6),
            "task_id": task_id,
            "summary": summary,
        }
        with open(self._billing_file(server_id), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def get_billing(self, server_id: str, month: str = None) -> dict:
        """查询账单。month 格式 YYYY-MM，不传则本月"""
        if month is None:
            month = datetime.now().strftime("%Y-%m")
        billing_file = self._billing_file(server_id)
        if not billing_file.exists():
            return {"total": 0, "by_agent": {}, "entries": []}

        entries = []
        with open(billing_file, encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                    if e["timestamp"].startswith(month):
                        entries.append(e)
                except Exception:
                    pass

        by_agent = {}
        total = 0
        for e in entries:
            name = e["agent"]
            if name not in by_agent:
                by_agent[name] = {"cost": 0, "tokens": 0, "calls": 0, "position": e["position"], "model": e["model"]}
            by_agent[name]["cost"] += e["cost"]
            by_agent[name]["tokens"] += e["tokens"]
            by_agent[name]["calls"] += 1
            total += e["cost"]

        return {
            "total": round(total, 4),
            "by_agent": by_agent,
            "entries": entries[-50:],  # 最近 50 条
        }

    # ========== 记事 ==========

    def _events_file(self, server_id: str) -> Path:
        return self.data_dir / f"events_{server_id}.jsonl"

    def record_event(self, server_id: str, agent_name: str, position: str,
                     action: str, summary: str, files: list = None,
                     task_id: str = "", cost: float = 0, status: str = "completed") -> dict:
        """记录一个事件"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "server_id": server_id,
            "agent": agent_name,
            "position": position,
            "action": action,         # "修复bug"、"生成图片"、"分析数据"
            "summary": summary,       # 一句话摘要
            "files": files or [],
            "task_id": task_id,
            "cost": cost,
            "status": status,         # completed | failed | in_progress
        }
        with open(self._events_file(server_id), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        # V9 注入：同步写入 agent_actions 表
        try:
            from core.lib.code_entity_extractor import extractor
            extractor.insert_agent_action(
                session_id=server_id,
                task_name=task_id or action[:80],
                tool_name=agent_name,
                result=status,
                file_type="ledger",
                agent_reaction="",
                detail=summary[:200]
            )
        except Exception:
            pass
        return entry

    def get_timeline(self, server_id: str, limit: int = 30) -> list:
        """获取时间线"""
        events_file = self._events_file(server_id)
        if not events_file.exists():
            return []

        entries = []
        with open(events_file, encoding="utf-8") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
        return sorted(entries, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def search_events(self, server_id: str, query: str, limit: int = 10) -> list:
        """搜索事件（简单关键词匹配）"""
        events_file = self._events_file(server_id)
        if not events_file.exists():
            return []

        results = []
        with open(events_file, encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                    text = json.dumps(e, ensure_ascii=False).lower()
                    if query.lower() in text:
                        results.append(e)
                except Exception:
                    pass
        return sorted(results, key=lambda x: x["timestamp"], reverse=True)[:limit]


# ========== 全局单例 ==========
ledger = Ledger()

# P0: 收编注册到 V9Context 容器(零行为变化 — 容器持有同一实例, 业务代码仍直接 import ledger)
try:
    from core.os.context import get_v9_context as _get_v9_ctx_ledger
    _get_v9_ctx_ledger().provide("ledger", ledger)
except Exception as _ledger_ctx_err:
    print(f"[LEDGER] P0 容器收编失败(不影响运行): {_ledger_ctx_err}")
