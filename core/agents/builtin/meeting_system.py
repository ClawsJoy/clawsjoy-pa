#!/usr/bin/env python3
"""Meeting System - Meeting System 模块

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

"""会议系统 - 多 Agent 协同解决问题"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List


class MeetingLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class MeetingSystem:
    """会议系统 - 协调多个 Agent 解决问题"""

    VERSION = "1.0.0"

    def __init__(self):
        self._load_meetings()
        print(f"📞 会议系统 v{self.VERSION} 已启动")

    def _load_meetings(self):
        meeting_file = Path(f"{get_data_root()}/meeting_records.json")
        if meeting_file.exists():
            with open(meeting_file, "r") as f:
                data = json.load(f)
                # 确保数据结构正确
                if isinstance(data, list):
                    self.meetings = {"meetings": data, "resolutions": []}
                else:
                    self.meetings = data
        else:
            self.meetings = {"meetings": [], "resolutions": []}

        # 确保 meetings 字段存在
        if "meetings" not in self.meetings:
            self.meetings["meetings"] = []
        if "resolutions" not in self.meetings:
            self.meetings["resolutions"] = []

    def _save_meetings(self):
        meeting_file = Path(f"{get_data_root()}/meeting_records.json")
        meeting_file.parent.mkdir(parents=True, exist_ok=True)
        with open(meeting_file, "w") as f:
            json.dump(self.meetings, f, indent=2, default=str)

    def trigger_meeting(self, issue: Dict, level: MeetingLevel) -> Dict:
        """触发会议"""
        meeting_id = f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        meeting = {
            "id": meeting_id,
            "level": level.value,
            "issue": issue,
            "triggered_at": datetime.now().isoformat(),
            "status": "started",
            "participants": [],
            "discussions": [],
            "resolutions": [],
        }

        # 根据问题类型决定参与者
        if issue.get("type") == "vector_mismatch":
            meeting["participants"] = [
                "auditor",
                "analyst",
                "decision_maker",
                "translator",
            ]
            meeting["agenda"] = [
                "1. 审计师汇报数据差异",
                "2. 分析师分析原因",
                "3. 语言大师检查翻译精准度",
                "4. 决策师给出修复方案",
            ]
        elif issue.get("type") == "translation_inaccuracy":
            meeting["participants"] = ["translator", "analyst", "decision_maker"]
            meeting["agenda"] = [
                "1. 语言大师汇报翻译问题",
                "2. 分析师评估影响范围",
                "3. 决策师确认优化方向",
            ]
        else:
            meeting["participants"] = ["analyst", "decision_maker"]
            meeting["agenda"] = ["1. 分析问题", "2. 制定方案"]

        self.meetings["meetings"].append(meeting)
        self._save_meetings()

        print(f"\n📞 会议已触发 [{level.value.upper()}]")
        print(f"   会议ID: {meeting_id}")
        print(f"   参与者: {', '.join(meeting['participants'])}")
        print(f"   议程: {meeting['agenda']}")

        return meeting

    def record_discussion(self, meeting_id: str, speaker: str, content: str):
        """记录会议讨论"""
        for meeting in self.meetings["meetings"]:
            if meeting["id"] == meeting_id:
                meeting["discussions"].append(
                    {
                        "speaker": speaker,
                        "content": content,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                break
        self._save_meetings()

    def close_meeting(self, meeting_id: str, resolution: Dict):
        """结束会议，记录决议"""
        for meeting in self.meetings["meetings"]:
            if meeting["id"] == meeting_id:
                meeting["status"] = "closed"
                meeting["closed_at"] = datetime.now().isoformat()
                meeting["resolution"] = resolution
                break

        self.meetings["resolutions"].append(
            {
                "meeting_id": meeting_id,
                "resolution": resolution,
                "resolved_at": datetime.now().isoformat(),
            }
        )
        self._save_meetings()

        print(f"\n✅ 会议 {meeting_id} 已结束")
        print(f"   决议: {resolution.get('action', 'unknown')}")

        return resolution

    def get_meeting_history(self, limit: int = 10) -> List[Dict]:
        """获取会议历史"""
        return self.meetings["meetings"][-limit:]


meeting_system = MeetingSystem()
