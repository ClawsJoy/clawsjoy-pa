#!/usr/bin/env python3
"""Workspace Manager - Workspace Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class WorkspaceManager:
    """Agent 工作区管理器"""

    _instance = None
    _workspaces: Dict[str, Dict] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._workspaces_loaded = False
        """初始化，扫描工作区"""
        self._scan_workspaces()
        print(f"✅ 工作区管理器初始化完成，共 {len(self._workspaces)} 个工作区")

    def _scan_workspaces(self):
        """扫描 agents/ 目录，发现工作区"""
        agents_dir = Path("agents")
        if not agents_dir.exists():
            return

        for agent_dir in agents_dir.iterdir():
            if agent_dir.is_dir():
                self._load_workspace(agent_dir)

    def _load_workspace(self, path: Path):
        """加载工作区配置"""
        config_file = path / "config.yaml"
        if not config_file.exists():
            return

        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)

            agent_name = config.get("agent", {}).get("name", path.name)

            self._workspaces[agent_name] = {
                "name": agent_name,
                "path": str(path),
                "config": config,
                "enabled": config.get("agent", {}).get("enabled", True),
                "memory_path": str(
                    path / config.get("memory", {}).get("path", "memory")
                ),
                "data_path": str(path / "data"),
                "skills_path": str(path / "skills"),
            }

            print(f"   📁 加载工作区: {agent_name} -> {path}")

        except Exception as e:
            print(f"   ⚠️ 加载工作区失败 {path}: {e}")

    def _load_workspaces(self):
        if self._workspaces_loaded:
            return
        self._scan_workspaces()
        self._workspaces_loaded = True

    def get_workspace(self, agent_name: str) -> Optional[Dict]:
        """获取工作区配置"""
        return self._workspaces.get(agent_name)

    def get_agent_config(self, agent_name: str) -> Optional[Dict]:
        """获取 Agent 的行为配置"""
        workspace = self.get_workspace(agent_name)
        if workspace:
            return workspace.get("config", {}).get("agent", {})
        return None

    def get_behavior_config(self, agent_name: str) -> Optional[Dict]:
        """获取 Agent 的行为配置（路由、分解等）"""
        workspace = self.get_workspace(agent_name)
        if workspace:
            config = workspace.get("config", {})
            # 返回除 agent 基础信息外的配置
            return {k: v for k, v in config.items() if k != "agent"}
        return None

    def list_workspaces(self) -> list:
        """列出所有工作区"""
        return list(self._workspaces.keys())

    def is_enabled(self, agent_name: str) -> bool:
        """检查工作区是否启用"""
        workspace = self.get_workspace(agent_name)
        return workspace.get("enabled", False) if workspace else False


# 全局实例
workspace_manager = WorkspaceManager()
