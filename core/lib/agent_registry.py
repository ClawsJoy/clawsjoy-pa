#!/usr/bin/env python3
"""Agent Registry - Agent Registry 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""Agent 注册中心 - 修复版"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class AgentRegistry:
    """Agent 注册中心"""

    VERSION = "1.0.0"

    def __init__(self, registry_file: str = f"{get_data_root()}/agent_registry.json"):
        self.registry_file = Path(registry_file)
        self.agents = self._load()

    def _load(self) -> Dict:
        """加载注册表"""
        if self.registry_file.exists():
            with open(self.registry_file, "r") as f:
                data = json.load(f)
                # 兼容不同格式
                if isinstance(data, dict) and "agents" in data:
                    return data["agents"]
                return data if isinstance(data, dict) else {}
        return {}

    def _save(self):
        """保存注册表"""
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_file, "w") as f:
            json.dump(self.agents, f, indent=2)

    def register(self, agent_id: str, agent_info: Dict) -> bool:
        """注册 Agent"""
        self.agents[agent_id] = {
            **agent_info,
            "registered_at": datetime.now().isoformat(),
            "status": "active",
        }
        self._save()

        # 注册到向量库（用于智能路由）
        try:
            from core.lib.vector_knowledge_center import vector_knowledge_center

            capability_desc = f"Agent: {agent_id}\n类型: {agent_info.get('type', 'custom')}\n描述: {agent_info.get('description', '')}\n能力: {agent_info.get('capabilities', [])}"
            vector_knowledge_center.add_agent_capability(
                agent_name=agent_id,
                capability_desc=capability_desc,
                user_id=agent_info.get("user_id", "system"),
            )
            print(f"✅ 向量注册: {agent_id}")
        except Exception as e:
            print(f"⚠️ 向量注册失败: {e}")

        return True

    def unregister(self, agent_id: str) -> bool:
        """注销 Agent"""
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = "inactive"
            self.agents[agent_id]["unregistered_at"] = datetime.now().isoformat()
            self._save()
            return True
        return False

    def get(self, agent_id: str) -> Optional[Dict]:
        """获取 Agent 信息"""
        return self.agents.get(agent_id)

    def list_all(self) -> Dict:
        """列出所有 Agent"""
        return self.agents

    def get_active(self) -> List[str]:
        """获取活跃 Agent 列表"""
        return [
            aid for aid, info in self.agents.items() if info.get("status") == "active"
        ]

    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "total": len(self.agents),
            "active": len(self.get_active()),
            "agents": list(self.agents.keys()),
        }


if __name__ == "__main__":
    print(f"Agent 注册中心 v{agent_registry.VERSION}")

    # 测试注册
    agent_registry.register("test_agent", {"name": "测试Agent", "type": "test"})
    print(f"已注册: {agent_registry.list_all()}")
    print(f"统计: {agent_registry.get_stats()}")

agent_registry = AgentRegistry()
