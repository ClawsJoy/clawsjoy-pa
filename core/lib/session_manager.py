#!/usr/bin/env python3
"""Session Manager - Session Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""
会话管理器 - 解决退出后无法登录的问题
"""

import time
from collections import defaultdict
from datetime import datetime

from flask import g, request, session


class SessionManager:
    """会话管理器 - 自动清理过期会话"""

    def __init__(self):
        self.sessions = defaultdict(dict)
        self.session_timeout = 3600  # 1小时

    def create_session(self, user_id, token):
        """创建会话"""
        self.sessions[token] = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_active": time.time(),
        }
        return token

    def validate_session(self, token):
        """验证会话"""
        if token not in self.sessions:
            return False
        session_data = self.sessions[token]
        # 检查是否过期
        if time.time() - session_data["last_active"] > self.session_timeout:
            del self.sessions[token]
            return False
        session_data["last_active"] = time.time()
        return True

    def invalidate_session(self, token):
        """使会话失效（登出时调用）"""
        if token in self.sessions:
            del self.sessions[token]
            return True
        return False

    def cleanup_expired(self):
        """清理过期会话"""
        expired = []
        for token, data in self.sessions.items():
            if time.time() - data["last_active"] > self.session_timeout:
                expired.append(token)
        for token in expired:
            del self.sessions[token]
        return len(expired)

    def list_sessions(self, user_id):
        """列出用户的所有 session（从文件系统扫描）"""
        from pathlib import Path

        project_dir = Path(f"data/projects/{user_id}")
        if not project_dir.exists():
            return []
        sessions = []
        for d in project_dir.iterdir():
            if d.is_dir() and (d / "clawsjoy_dev").exists():
                sessions.append(
                    {"session_id": d.name, "created_at": datetime.fromtimestamp(d.stat().st_mtime).isoformat()}
                )
        return sorted(sessions, key=lambda s: s["created_at"], reverse=True)


session_manager = SessionManager()
