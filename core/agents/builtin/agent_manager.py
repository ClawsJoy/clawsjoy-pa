#!/usr/bin/env python3
"""Agent Manager - 懒加载版本"""

from pathlib import Path
from typing import Dict, Optional

import yaml


class AgentManager:
    """Agent 管理器 - 懒加载"""

    _instance = None
    _agents = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        # 轻量级初始化，不加载数据
        self.registry_dir = Path("config/agents/registry")
        print("✅ Agent 管理器已初始化（轻量级）")

    def _load_agents(self):
        """延迟加载 Agent 配置"""
        if self._agents is not None:
            return

        self._agents = {}
        if not self.registry_dir.exists():
            return

        for config_file in self.registry_dir.glob("*.yaml"):
            if config_file.name.endswith(".bak"):
                continue
            try:
                with open(config_file, "r") as f:
                    data = yaml.safe_load(f)
                    agent_name = data.get("name")
                    if agent_name and data.get("enabled", True):
                        self._agents[agent_name] = data
            except Exception as e:
                pass

        print(f"✅ Agent 管理器加载完成，共 {len(self._agents)} 个 Agent")

    @property
    def agents(self) -> Dict:
        """获取所有 Agent（触发懒加载）"""
        self._load_agents()
        return self._agents

    def get_agent(self, agent_name: str) -> Optional[Dict]:
        """获取 Agent 配置"""
        self._load_agents()
        return self._agents.get(agent_name)

    def list_agents(self) -> list:
        """列出所有 Agent"""
        self._load_agents()
        return list(self._agents.keys())

    def reload(self):
        """重新加载配置"""
        self._agents = None
        self._load_agents()


# 全局实例（懒加载）
_agent_manager = None


def get_agent_manager() -> AgentManager:
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
    return _agent_manager


# 兼容旧代码
agent_manager = None
