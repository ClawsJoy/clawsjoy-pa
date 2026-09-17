#!/usr/bin/env python3
"""Meeting Records - Meeting Records 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config

"""会议记录查询"""
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.lib.agent_meeting import agent_meeting
from core.lib.memory_vector import vector_memory


class MeetingRecords:
    """会议记录管理器"""

    def __init__(self):
        self.records_file = Path(f"{get_data_root()}/meeting_records.json")
        self._load()

    def _load(self):
        if self.records_file.exists():
            import json

            with open(self.records_file, "r") as f:
                self.records = json.load(f)
        else:
            self.records = {"meetings": [], "stats": {"total": 0}}

    def _save(self):
        import json

        with open(self.records_file, "w") as f:
            json.dump(self.records, f, indent=2)

    def add_record(self, meeting_id: str, topic: str, decisions: List[Dict]):
        """添加会议记录"""
        record = {
            "meeting_id": meeting_id,
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "decisions": decisions,
            "status": "closed",
        }
        self.records["meetings"].append(record)
        self.records["stats"]["total"] += 1
        self._save()

        # 同时存到向量记忆
        vector_memory.add(
            text=f"会议记录: {topic} | 决策数: {len(decisions)}",
            category="meeting_record",
            metadata={"meeting_id": meeting_id, "topic": topic},
        )

    def query(self, keyword: str = None, limit: int = 10) -> List[Dict]:
        """查询会议记录"""
        results = []

        # 从向量记忆语义搜索
        if keyword:
            search_results = vector_memory.search(
                keyword, category="meeting_record", n=limit
            )
            for r in search_results:
                results.append(
                    {
                        "meeting_id": r["metadata"].get("meeting_id"),
                        "topic": r["metadata"].get("topic"),
                        "similarity": r["similarity"],
                    }
                )

        # 补充本地记录
        for record in self.records["meetings"][-limit:]:
            if not keyword or keyword in record["topic"]:
                if not any(
                    r.get("meeting_id") == record["meeting_id"] for r in results
                ):
                    results.append(record)

        return results[:limit]

    def get_by_id(self, meeting_id: str) -> Optional[Dict]:
        """根据ID获取会议记录"""
        for record in self.records["meetings"]:
            if record["meeting_id"] == meeting_id:
                return record
        return None

    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "total_meetings": self.records["stats"]["total"],
            "latest_meeting": (
                self.records["meetings"][-1] if self.records["meetings"] else None
            ),
        }


meeting_records = MeetingRecords()
