#!/usr/bin/env python3
"""Agent 能力描述加载器"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional


class AgentCapabilityLoader:
    """加载 Agent 能力描述，用于 LLM 提示词"""

    def __init__(self, config_dir: str = "config/agents/capabilities"):
        self.config_dir = Path(config_dir)
        self._cache: Dict[str, Dict] = {}

    def load_all(self) -> Dict[str, Dict]:
        """加载所有 Agent 能力描述"""
        if self._cache:
            return self._cache

        if not self.config_dir.exists():
            return {}

        for file_path in self.config_dir.glob("*.yaml"):
            try:
                with open(file_path, 'r') as f:
                    data = yaml.safe_load(f)
                    if data:
                        name = data.get('name', file_path.stem)
                        self._cache[name] = data
            except Exception as e:
                print(f"加载 {file_path} 失败: {e}")

        return self._cache

    def get(self, agent_name: str) -> Optional[Dict]:
        """获取指定 Agent 的能力描述"""
        self.load_all()
        return self._cache.get(agent_name)

    def get_capability_prompt(self, agent_name: str = None) -> str:
        """生成 LLM 友好的能力提示词"""
        all_agents = self.load_all()

        if agent_name:
            agent = all_agents.get(agent_name)
            if not agent:
                return ""
            return self._format_agent_prompt(agent)

        # 生成所有 Agent 的列表
        lines = []
        for name, agent in all_agents.items():
            lines.append(f"- {name}: {agent.get('description', '')}")
            for cap in agent.get('capabilities', []):
                lines.append(f"    - {cap.get('name')}: {cap.get('description')}")

        return "\n".join(lines)

    def _format_agent_prompt(self, agent: Dict) -> str:
        """格式化单个 Agent 的提示词"""
        lines = [
            f"Agent: {agent.get('name', 'unknown')}",
            f"描述: {agent.get('description', '')}",
            "能力:"
        ]
        for cap in agent.get('capabilities', []):
            lines.append(f"  - {cap.get('name')}: {cap.get('description')}")

        if agent.get('examples'):
            lines.append("示例:")
            for ex in agent.get('examples', []):
                lines.append(f"  输入: {ex.get('input', '')}")
                lines.append(f"  输出: {ex.get('output', '')}")

        return "\n".join(lines)

    def get_recommendation_prompt(self, user_input: str) -> str:
        """生成 Agent 推荐提示词"""
        all_agents = self.load_all()

        prompt = f"""用户请求: {user_input}

请从以下 Agent 中选择最合适的一个来处理这个请求。

可用 Agent:
"""
        for name, agent in all_agents.items():
            prompt += f"- {name}: {agent.get('description', '')}\n"

        prompt += """
只输出 Agent 名称，不要解释。
如果不确定，输出: orchestrator

推荐:"""
        return prompt


# 全局实例
agent_capability_loader = AgentCapabilityLoader()
