#!/usr/bin/env python3
"""Guest Token Manager - Guest Token Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import hashlib
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class GuestTokenManager:
    """游客 Token 管理器 - 自动生成，关联脱敏数据"""

    def __init__(self):
        self._sessions: Dict[str, dict] = {}
        self._token_ttl = 300  # 5分钟有效期
        self._analytics_dir = Path("data/analytics/guests")
        self._analytics_dir.mkdir(parents=True, exist_ok=True)

    def create_session(self) -> dict:
        """创建新的游客会话"""
        token = self._generate_token()
        session = {
            "token": token,
            "user_id": f"guest_{token[:16]}",
            "created_at": time.time(),
            "expires_at": time.time() + self._token_ttl,
            "interactions": 0,
            "session_id": str(uuid.uuid4()),
        }
        self._sessions[token] = session

        # 记录会话创建（脱敏）
        self._record_analytics("session_created", session)

        return session

    def validate_token(self, token: str) -> Optional[dict]:
        """验证 token 是否有效"""
        session = self._sessions.get(token)
        if not session:
            return None
        if time.time() > session["expires_at"]:
            # token 过期，记录过期事件
            self._record_analytics("session_expired", session)
            del self._sessions[token]
            return None
        # 更新最后活跃时间
        session["last_active"] = time.time()
        session["interactions"] += 1
        return session

    def renew_session(self, old_token: str = None) -> dict:
        """创建新会话（5分钟沉默后调用）"""
        old_session = None
        if old_token and old_token in self._sessions:
            old_session = self._sessions[old_token]

        # 创建新会话
        new_session = self.create_session()

        if old_session:
            # 关联旧会话数据（用于分析游客行为链）
            new_session["previous_session_id"] = old_session.get("session_id")
            new_session["previous_interactions"] = old_session.get("interactions", 0)

            # 记录会话续期事件
            self._record_analytics(
                "session_renewed",
                {
                    "old_session_id": old_session.get("session_id"),
                    "new_session_id": new_session["session_id"],
                    "old_interactions": old_session.get("interactions", 0),
                },
            )

            # 删除旧会话
            del self._sessions[old_token]

        return new_session

    def record_interaction(self, token: str, user_input: str, response: str) -> bool:
        """记录游客交互（脱敏，用于市场分析）"""
        session = self.validate_token(token)
        if not session:
            return False

        # 脱敏处理
        from core.lib.security_hooks import SecurityHooks

        hooks = SecurityHooks()

        context = {
            "data": {
                "session_id": session.get("session_id"),
                "user_input": user_input,
                "response": response,
                "interaction_count": session.get("interactions", 0),
            }
        }

        # 调用脱敏钩子
        try:
            redacted = hooks.redact_sensitive(context)
            data = redacted.get("data", {})
        except Exception as e:
            data = context["data"]

        # 存储到分析数据（JSON Lines 格式）
        record = {
            "timestamp": time.time(),
            "date": datetime.now().isoformat(),
            "session_id": data.get("session_id"),
            "user_input": data.get("user_input", "")[:500],
            "response_length": len(data.get("response", "")),
            "interaction_count": data.get("interaction_count", 0),
        }

        analytics_file = self._analytics_dir / f"{session.get('session_id')}.jsonl"
        with open(analytics_file, "a") as f:
            f.write(json.dumps(record) + "\n")

        # 同时写入全局汇总（用于市场分析）
        global_file = self._analytics_dir / "_all_interactions.jsonl"
        with open(global_file, "a") as f:
            f.write(json.dumps(record) + "\n")

        return True

    def _record_analytics(self, event_type: str, data: dict):
        """记录分析事件"""
        record = {
            "timestamp": time.time(),
            "date": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data,
        }
        event_file = self._analytics_dir / "_events.jsonl"
        with open(event_file, "a") as f:
            f.write(json.dumps(record) + "\n")

    def _generate_token(self) -> str:
        """生成唯一 token"""
        return hashlib.md5(f"{uuid.uuid4()}{time.time()}".encode()).hexdigest()

    def get_stats(self) -> dict:
        """获取统计"""
        return {
            "active_sessions": len(self._sessions),
            "token_ttl": self._token_ttl,
            "analytics_dir": str(self._analytics_dir),
        }


guest_token_manager = GuestTokenManager()
