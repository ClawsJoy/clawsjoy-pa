#!/usr/bin/env python3
"""动态 Agent 路由 - 自动发现和调用"""

import importlib
import inspect
from pathlib import Path
from typing import Dict, Optional

class DynamicRouter:
    """动态路由器"""
    
    def __init__(self):
        self.agents = {}
        self._discover_agents()
    
    def _discover_agents(self):
        """自动发现所有 Agent"""
        agents_dir = Path(__file__).parent.parent / "agents"
        for agent_dir in agents_dir.iterdir():
            if not agent_dir.is_dir() or agent_dir.name.startswith("__"):
                continue
            
            agent_name = agent_dir.name
            agent_file = agent_dir / "agent.py"
            if agent_file.exists():
                try:
                    spec = importlib.util.spec_from_file_location(agent_name, agent_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # 查找 Agent 类
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj):
                            if hasattr(obj, 'process') or hasattr(obj, 'handle'):
                                self.agents[agent_name] = {
                                    "class": obj,
                                    "module": module,
                                    "name": agent_name
                                }
                                print(f"✅ 发现 Agent: {agent_name}")
                                break
                except Exception as e:
                    print(f"⚠️ 加载 {agent_name} 失败: {e}")
    
    def route(self, intent: str, message: str, user_id: str = "default") -> Dict:
        """动态路由"""
        # 根据意图映射到 Agent
        intent_to_agent = {
            "code": "code_agent",
            "translate": "chat_agent",
            "calculate": "chat_agent",
            "long_task": "orchestrator",
            "chat": "chat_agent"
        }
        
        agent_name = intent_to_agent.get(intent, "chat_agent")
        agent_info = self.agents.get(agent_name)
        
        if agent_info:
            try:
                agent = agent_info["class"]()
                if hasattr(agent, 'process'):
                    return agent.process(message, {"user_id": user_id})
                elif hasattr(agent, 'handle'):
                    return agent.handle(message)
            except Exception as e:
                return {"error": str(e)}
        
        return {"response": f"Agent {agent_name} 未找到"}

router = DynamicRouter()
