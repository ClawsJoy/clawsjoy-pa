#!/usr/bin/env python3
"""Agent Soul - Agent Soul 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from pathlib import Path
from typing import Dict, Optional

import yaml


class AgentSoul:
    """Agent 灵魂配置管理"""

    _instance = None
    _souls: Dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _find_file(self, candidates: list) -> Optional[Path]:
        """查找配置文件"""
        for candidate in candidates:
            path = Path(candidate)
            if path.exists():
                return path
        return None

    def _load(self):
        """加载灵魂配置"""
        candidates = [
            "config/agents_soul/agents_soul.yaml",
            "config/agents_soul/agents_soul.yaml",
        ]
        soul_file = self._find_file(candidates)
        if soul_file:
            try:
                with open(soul_file, "r") as f:
                    data = yaml.safe_load(f)
                    self._souls = data.get("agents", {})
                print(f"   ✅ 加载 Agent 灵魂配置: {len(self._souls)} 个")
            except Exception as e:
                print(f"   ⚠️ 加载灵魂配置失败: {e}")

    def get_soul(self, agent_name: str) -> Optional[Dict]:
        """获取 Agent 灵魂配置"""
        return self._souls.get(agent_name)

    def get_personality(self, agent_name: str) -> str:
        """获取 Agent 人格"""
        soul = self.get_soul(agent_name)
        if soul:
            return soul.get("persona", "default")
        return "default"


agent_soul = AgentSoul()
