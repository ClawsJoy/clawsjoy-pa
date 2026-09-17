#!/usr/bin/env python3
"""WebSocket 实时协作 - 基础框架"""

import json
from typing import Dict, Set, List
from datetime import datetime


class CollaborationManager:
    """协作管理器"""

    def __init__(self):
        self.sessions: Dict[str, Set[str]] = {}  # project_id -> set of user_ids
        self.users: Dict[str, Dict] = {}  # user_id -> session info

    def join(self, project_id: str, user_id: str) -> Dict:
        """加入协作"""
        if project_id not in self.sessions:
            self.sessions[project_id] = set()
        self.sessions[project_id].add(user_id)
        
        self.users[user_id] = {
            "project": project_id,
            "joined_at": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "message": f"{user_id} 加入了协作",
            "users": list(self.sessions[project_id])
        }

    def leave(self, project_id: str, user_id: str) -> Dict:
        """离开协作"""
        if project_id in self.sessions:
            self.sessions[project_id].discard(user_id)
        
        return {
            "success": True,
            "message": f"{user_id} 离开了协作",
            "users": list(self.sessions.get(project_id, []))
        }

    def broadcast(self, project_id: str, sender: str, message: str) -> Dict:
        """广播消息"""
        if project_id not in self.sessions:
            return {"success": False, "error": "会话不存在"}
        
        return {
            "success": True,
            "sender": sender,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "users": list(self.sessions[project_id])
        }

    def get_users(self, project_id: str) -> List[str]:
        """获取在线用户"""
        return list(self.sessions.get(project_id, []))


# 全局实例
collaboration_manager = CollaborationManager()
