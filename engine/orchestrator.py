#!/usr/bin/env python3
"""Orchestrator - Orchestrator 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List

from core.lib.unified_config import unified_config


class CollaborationOrchestrator:
    """多Agent协作编排器 - 按原设计"""

    VERSION = "1.0.0"

    def __init__(self):
        self.sessions = {}
        self.lock = Lock()
        self.collaboration_log = Path(
            f"{config_helper.get_data_root()}/collaboration/collaborations.json"
        )
        self._init_storage()
        print(f"🤝 多Agent协作编排器 v{self.VERSION} 已启动")

    def _init_storage(self):
        Path(f"{config_helper.get_data_root()}/collaboration").mkdir(
            parents=True, exist_ok=True
        )
        if not self.collaboration_log.exists():
            self._save([])

    def _save(self, data):
        with open(self.collaboration_log, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self):
        if self.collaboration_log.exists():
            with open(self.collaboration_log, "r") as f:
                return json.load(f)
        return []

    def create_collaboration(
        self, topic: str, agents: List[str], initiator: str = "user"
    ) -> Dict:
        """创建协作会话"""
        with self.lock:
            session_id = f"collab_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            session = {
                "id": session_id,
                "topic": topic,
                "agents": agents,
                "initiator": initiator,
                "status": "active",
                "messages": [],
                "decisions": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            self.sessions[session_id] = session

            # 记录日志
            history = self._load()
            history.append(
                {
                    "action": "create",
                    "session": session_id,
                    "topic": topic,
                    "agents": agents,
                }
            )
            self._save(history)

            print(f"📋 创建协作会话: {session_id} (议题: {topic})")
            return session

    def add_message(self, session_id: str, agent: str, message: str) -> Dict:
        """添加协作消息"""
        if session_id not in self.sessions:
            return {"error": "会话不存在"}

        session = self.sessions[session_id]
        msg = {
            "agent": agent,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        session["messages"].append(msg)
        session["updated_at"] = datetime.now().isoformat()

        return {"success": True, "session_id": session_id}

    def make_decision(
        self, session_id: str, decision: str, confidence: float = 0.8
    ) -> Dict:
        """做出协作决策"""
        if session_id not in self.sessions:
            return {"error": "会话不存在"}

        session = self.sessions[session_id]
        decision_record = {
            "decision": decision,
            "confidence": confidence,
            "made_at": datetime.now().isoformat(),
            "by": "collaboration",
        }
        session["decisions"].append(decision_record)
        session["status"] = "completed"
        session["updated_at"] = datetime.now().isoformat()

        # 记录历史
        history = self._load()
        history.append(
            {"action": "decision", "session": session_id, "decision": decision}
        )
        self._save(history)

        return {"success": True, "decision": decision, "confidence": confidence}

    def get_session(self, session_id: str) -> Dict:
        """获取会话详情"""
        return self.sessions.get(session_id, {"error": "会话不存在"})

    def get_active_sessions(self) -> List[Dict]:
        """获取活跃会话"""
        return [s for s in self.sessions.values() if s["status"] == "active"]


collaboration = CollaborationOrchestrator()
