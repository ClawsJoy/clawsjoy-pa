#!/usr/bin/env python3
"""Collector Agent - Collector Agent 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import sys

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config

sys.path.insert(0, "unified_config.ROOT")
#!/usr/bin/env python3
"""采集 Agent - 配置驱动版"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from agents.base_agent import BaseAgent

from core.lib.config_manager import config_manager

config = config_manager
from core.lib.config_manager import config_manager
from core.lib.unified_config import unified_config


class CollectorAgent(SmartAgent):
    """采集 Agent - 配置驱动"""

    VERSION = "1.0.0"

    def __init__(self):
        super().__init__("CollectorAgent")
        self._load_config()
        self.sessions = {}
        self.user_preferences = self._load_preferences()
        self.log(f"采集 Agent 初始化完成")

    def process(
        self, user_input: str, context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """实现抽象方法"""
        return {
            "success": True,
            "message": "采集 Agent 已接收",
            "version": self.VERSION,
        }

    def _load_config(self):
        """从配置加载参数模板"""
        # 直接从 YAML 文件加载，避免 config_loader 问题
        config_file = Path("config/driver/collector.yaml")
        if config_file.exists():
            collector_config = unified_config.get("driver", {}).get("collector", {})
            self.skill_templates = collector_config.get("skill_templates", {})
            self.collection_config = collector_config.get("collection", {})
            self.prefs_config = collector_config.get("user_preferences", {})
        else:
            self.skill_templates = {}
            self.collection_config = {}
            self.prefs_config = {}

        self.log(f"加载技能模板: {len(self.skill_templates)} 个")

    def _load_preferences(self) -> Dict:
        """加载用户偏好"""
        storage = self.prefs_config.get(
            "storage", f"{get_data_root()}/user_preferences.json"
        )
        pref_file = Path(storage)
        if pref_file.exists():
            with open(pref_file, "r") as f:
                return json.load(f)
        return {}

    def _save_preferences(self):
        """保存用户偏好"""
        if not self.prefs_config.get("auto_save", True):
            return
        storage = self.prefs_config.get(
            "storage", f"{get_data_root()}/user_preferences.json"
        )
        pref_file = Path(storage)
        pref_file.parent.mkdir(parents=True, exist_ok=True)
        with open(pref_file, "w") as f:
            json.dump(self.user_preferences, f, indent=2, ensure_ascii=False)

    def start_session(
        self, session_id: str, skill: str, user_id: str = "default"
    ) -> Optional[Dict]:
        """开始新会话"""
        template = self.skill_templates.get(skill)
        if not template:
            self.log(f"技能 {skill} 无参数模板")
            return None

        required = template.get("required_params", [])

        # 从用户偏好预填
        prefs = self.user_preferences.get(user_id, {}).get(skill, {})

        self.sessions[session_id] = {
            "skill": skill,
            "user_id": user_id,
            "collected": prefs.copy(),
            "required_names": [p["name"] for p in required],
            "template": required,
            "started_at": datetime.now().isoformat(),
            "status": "collecting",
        }

        self.log(f"开始会话 {session_id}, 技能: {skill}")
        return self._get_next_question(session_id)

    def _get_next_question(self, session_id: str) -> Optional[Dict]:
        """获取下一个问题"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        collected = session["collected"]

        for param in session["template"]:
            name = param["name"]
            if name not in collected:
                return {
                    "param": name,
                    "question": param["question"],
                    "options": param.get("options", []),
                    "examples": param.get("examples", []),
                }

        session["status"] = "complete"
        session["completed_at"] = datetime.now().isoformat()
        return None

    def update(self, session_id: str, param_name: str, value: str) -> Dict:
        """更新参数"""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "会话不存在", "status": "error"}

        session["collected"][param_name] = value

        # 保存到用户偏好
        user_id = session["user_id"]
        skill = session["skill"]
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        if skill not in self.user_preferences[user_id]:
            self.user_preferences[user_id][skill] = {}
        self.user_preferences[user_id][skill][param_name] = value
        self._save_preferences()

        # 获取下一个问题
        next_q = self._get_next_question(session_id)

        if next_q is None:
            return {
                "status": "complete",
                "collected": session["collected"],
                "message": "参数收集完成",
            }
        else:
            return {
                "status": "collecting",
                "next_question": next_q["question"],
                "options": next_q.get("options", []),
                "param": next_q["param"],
            }

    def get_collected(self, session_id: str) -> Optional[Dict]:
        """获取已收集的参数"""
        session = self.sessions.get(session_id)
        return session["collected"] if session else None

    def is_complete(self, session_id: str) -> bool:
        """检查是否完成"""
        session = self.sessions.get(session_id)
        return session and session.get("status") == "complete"

    def extract_from_text(self, text: str, param_name: str) -> Optional[str]:
        """从文本中提取参数值"""
        if param_name == "age":
            if "中年" in text or "40" in text or "50" in text:
                return "中年"
            if "青年" in text or "20" in text or "30" in text:
                return "青年"
            if "老年" in text or "60" in text:
                return "老年"
        elif param_name == "expression":
            for exp in ["坚毅", "温和", "开心", "严肃"]:
                if exp in text:
                    return exp
        elif param_name == "style":
            for style in ["写实", "卡通", "水墨", "油画"]:
                if style in text:
                    return style
        return None


# collector_agent = CollectorAgent()  # 注释：改为按需创建


if __name__ == "__main__":
    print(f"采集 Agent v{collector_agent.VERSION}")

    # 测试
    session_id = "test"
    collector_agent.start_session(session_id, "ai-image-gen", "test_user")

    for param, value in [
        ("subject", "漫剧人物"),
        ("age", "中年"),
        ("expression", "坚毅"),
        ("style", "写实"),
    ]:
        result = collector_agent.update(session_id, param, value)
        print(f"{param}: {result['status']}")

    print(f"\n收集结果: {collector_agent.get_collected(session_id)}")
    print(f"用户偏好: {collector_agent.user_preferences}")
