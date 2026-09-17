"""对话管理引擎 - 多轮对话 + 上下文跟踪"""

from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional

from engine.lib.logger import engine_logger


class DialogueEngine:
    """对话管理引擎"""

    def __init__(self):
        self.sessions = {}
        self.max_history = 20
        engine_logger.get().info("💬 对话管理引擎已初始化")

    def process(self, input_data: Any = None, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, dict):
            user_id = input_data.get("user_id", "default")
            text = input_data.get("text", "")
            response = input_data.get("response", "")
            intent = input_data.get("intent")
            if text and response:
                return self.add_turn(user_id, text, response, intent)
            return self.get_context(user_id)
        return self.get_context(str(input_data))

    def get_or_create_session(self, user_id: str) -> Dict:
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                "history": deque(maxlen=self.max_history),
                "state": {},
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
            }
        return self.sessions[user_id]

    def add_turn(
        self, user_id: str, user_input: str, assistant_output: str, intent: str = None
    ) -> Dict:
        session = self.get_or_create_session(user_id)
        turn = {
            "user": user_input,
            "assistant": assistant_output,
            "intent": intent,
            "timestamp": datetime.now().isoformat(),
        }
        session["history"].append(turn)
        session["last_active"] = datetime.now().isoformat()
        return {"turn_id": len(session["history"])}

    def get_context(self, user_id: str, turns: int = 5) -> List[Dict]:
        session = self.get_or_create_session(user_id)
        return list(session["history"])[-turns:]

    def get_state(self, user_id: str, key: str = None) -> Any:
        session = self.get_or_create_session(user_id)
        if key:
            return session["state"].get(key)
        return session["state"]

    def set_state(self, user_id: str, key: str, value: Any) -> Dict:
        session = self.get_or_create_session(user_id)
        session["state"][key] = value
        return {"success": True}

    def clear_session(self, user_id: str) -> Dict:
        if user_id in self.sessions:
            del self.sessions[user_id]
        return {"success": True}

    def get_stats(self) -> Dict:
        return {
            "active_sessions": len(self.sessions),
            "total_turns": sum(len(s["history"]) for s in self.sessions.values()),
            "status": "active",
        }

    def reload(self) -> Dict:
        self.sessions.clear()
        return {"success": True, "message": "Dialogue engine reloaded"}

    def health_check(self) -> Dict:
        return {"name": "dialogue_engine", "status": "healthy"}


dialogue_engine = DialogueEngine()
