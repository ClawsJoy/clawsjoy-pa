"""Agent 实例缓存管理器"""

import importlib
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AgentCache:
    """Agent 实例缓存（单例模式）"""

    _instance = None
    _user_instances: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get(self, agent_name: str, user_id: str = "default") -> Optional[Any]:
        """获取 Agent 实例（自动创建并缓存）"""
        key = f"{agent_name}:{user_id}"

        if key not in self._user_instances:
            self._user_instances[key] = self._create(agent_name, user_id)
            if self._user_instances[key]:
                logger.debug(f"✅ 创建 Agent: {agent_name} (user={user_id})")

        return self._user_instances.get(key)

    def _create(self, agent_name: str, user_id: str) -> Optional[Any]:
        """创建 Agent 实例"""
        try:
            module = importlib.import_module(f"agents.{agent_name}.agent")

            # 修复类名生成：chat_agent -> ChatAgent (不是 ChatAgentAgent)
            # 去掉末尾的 _agent，然后首字母大写
            if agent_name.endswith("_agent"):
                base_name = agent_name[:-6]  # 去掉 _agent
            else:
                base_name = agent_name

            class_name = "".join(w.capitalize() for w in base_name.split("_")) + "Agent"

            agent_class = getattr(module, class_name)
            return agent_class(user_id)
        except Exception as e:
            logger.error(f"创建 Agent {agent_name} 失败: {e}")
            return None

    def clear(self):
        """清理所有缓存"""
        self._user_instances.clear()
        logger.info("🗑️ Agent 缓存已清理")

    def size(self) -> int:
        return len(self._user_instances)

    def stats(self) -> dict:
        return {
            "cached_agents": self.size(),
            "agents": list(set(k.split(":")[0] for k in self._user_instances.keys())),
        }


# 全局单例
agent_cache = AgentCache()


def get_agent(agent_name: str, user_id: str = "default"):
    """快捷函数：获取 Agent 实例"""
    return agent_cache.get(agent_name, user_id)
