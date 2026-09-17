#!/usr/bin/env python3
"""Agent Meeting - Agent Meeting 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""Agent 会议系统 - 群体智能协作"""
import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from core.lib.agent_communication import agent_comm
from core.lib.closed_loop_config import closed_loop_config
from core.lib.memory_vector import vector_memory
from core.lib.skill_loader_v3 import skill_loader
from core.lib.unified_config import unified_config


@dataclass
class MeetingTopic:
    """会议主题"""

    title: str
    description: str
    complexity: str = "medium"
    proposed_by: str = "system"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MeetingDecision:
    """会议决策"""

    topic: str
    resolution: str
    action_items: List[Dict]
    votes: Dict
    consensus_reached: bool
    meeting_id: str


class AgentMeeting:
    """Agent 会议系统"""

    def __init__(self):
        self._load_config()
        self.active_meetings = {}
        self.meeting_history = []

    def _load_config(self):
        config_file = Path(__file__).parent.parent / "config/agent_meeting.yaml"
        if config_file.exists():
            with open(config_file, "r") as f:
                self.config = unified_config.get("agent_meeting", {})
        else:
            self.config = {"roles": {}, "meeting_flow": []}

    def convene(self, topic: MeetingTopic) -> str:
        """召集会议"""
        meeting_id = f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.active_meetings[meeting_id] = {
            "topic": topic,
            "status": "convened",
            "started_at": datetime.now().isoformat(),
            "discussions": [],
            "decisions": [],
        }

        vector_memory.add(
            text=f"会议召集: {topic.title}",
            category="meeting",
            metadata={"meeting_id": meeting_id, "topic": topic.title},
        )

        print(f"📢 会议召集: {topic.title} (ID: {meeting_id})")
        return meeting_id

    def discuss(self, meeting_id: str, agent: str, opinion: str) -> bool:
        if meeting_id not in self.active_meetings:
            return False

        self.active_meetings[meeting_id]["discussions"].append(
            {
                "agent": agent,
                "opinion": opinion,
                "timestamp": datetime.now().isoformat(),
            }
        )

        print(f"💬 {agent}: {opinion[:100]}...")
        return True

    def propose_solution(self, meeting_id: str, solution: Dict) -> bool:
        if meeting_id not in self.active_meetings:
            return False
        self.active_meetings[meeting_id]["proposed_solution"] = solution
        return True

    def vote(self, meeting_id: str, votes: Dict) -> Dict:
        if meeting_id not in self.active_meetings:
            return {"success": False}

        weights = self.config.get("consensus", {}).get("weighted_votes", {})
        threshold = self.config.get("consensus", {}).get("threshold", 0.6)

        total_weight = 0
        approved_weight = 0

        for agent, vote in votes.items():
            weight = weights.get(agent, 1.0)
            total_weight += weight
            if vote:
                approved_weight += weight

        consensus = (approved_weight / total_weight) >= threshold

        decision = {
            "meeting_id": meeting_id,
            "votes": votes,
            "consensus_reached": consensus,
            "approved_weight": approved_weight,
            "total_weight": total_weight,
            "timestamp": datetime.now().isoformat(),
        }

        self.active_meetings[meeting_id]["decisions"].append(decision)
        self.active_meetings[meeting_id]["status"] = (
            "closed" if consensus else "stalled"
        )

        return decision

    def decompose_task(self, task: str) -> List[Dict]:
        max_subtasks = self.config.get("task_decomposition", {}).get("max_subtasks", 5)

        prompt = f"""将以下复杂任务分解为 {max_subtasks} 个可执行的子任务:

任务: {task}

输出格式:
[
  {{"subtask": "子任务1", "estimated_time": 60, "dependencies": [], "suggested_agent": "agent_name"}},
  ...
]
"""
        try:
            from core.lib.smart_adapter import smart_adapter

            response = smart_adapter.generate(prompt, auto_select=True)
            import re

            match = re.search(r"\[.*\]", response, re.DOTALL)
            if match:
                subtasks = json.loads(match.group())
                return subtasks[:max_subtasks]
        except Exception as e:
            pass

        return [
            {
                "subtask": task,
                "estimated_time": 60,
                "dependencies": [],
                "suggested_agent": "orchestrator",
            }
        ]

    def close_meeting(self, meeting_id: str) -> Dict:
        if meeting_id not in self.active_meetings:
            return {"success": False}

        meeting = self.active_meetings[meeting_id]
        meeting["status"] = "closed"
        meeting["ended_at"] = datetime.now().isoformat()

        self.meeting_history.append(meeting)

        return {
            "success": True,
            "meeting_id": meeting_id,
            "decisions": meeting.get("decisions", []),
        }


agent_meeting = AgentMeeting()
