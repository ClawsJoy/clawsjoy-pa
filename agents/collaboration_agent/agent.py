from core.agents.business.business_agent_v2 import BusinessAgentV2
#!/usr/bin/env python3
"""协作智能体 - 增强版（多Agent并行协作、结果融合）"""

import concurrent.futures
import re
from typing import Any, Dict, List, Optional

from core.agents.business.base_business_agent import BusinessAgent


class CollaborationAgent(BusinessAgentV2):
    name = "collaboration_agent"
    description = "多智能体协作"
    version = "3.0.0"

    # Agent注册表
    AGENT_REGISTRY = {
        "代码": "code_agent",
        "编程": "code_agent",
        "分析": "analysis_agent",
        "数据": "analysis_agent",
        "决策": "decision_agent",
        "选择": "decision_agent",
        "执行": "executor_agent",
        "计算": "executor_agent",
        "翻译": "translate_agent",
        "方言": "dialect_agent",
        "视频": "video_agent",
        "视觉": "vision_agent",
        "写作": "writer_agent",
        "YouTube": "youtube_agent",
        "记忆": "memory_agent",
        "导演": "director_agent",
    }

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.collaboration_history = []
        print(f"🤝 协作智能体 v3.0 已上线")

    def _execute_business(self, user_input: str, context: dict = None) -> dict:
        """业务逻辑实现 - BusinessAgent 要求"""
        return self.process(user_input, context)

    def process(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        print(f"[协作] 收到: {user_input}")

        # 1. 智能Agent识别
        agents = self._identify_agents(user_input)

        # 2. 并行协作
        if agents and len(agents) > 1:
            results = self._parallel_collaborate(agents, user_input)
            fused = self._fuse_results(results)
            return {
                "success": True,
                "response": fused["response"],
                "collaboration": results,
                "fused_result": fused,
                "agents_involved": agents,
                "agent": self.name,
                "user_id": self.user_id,
            }

        # 3. 单一Agent委托
        if agents:
            result = self._delegate(agents[0], user_input)
            result["collaborated"] = True
            return result

        return self._help()

    def _identify_agents(self, text: str) -> List[str]:
        """识别需要的Agent"""
        agents = []
        for keyword, agent in self.AGENT_REGISTRY.items():
            if keyword in text and agent not in agents:
                agents.append(agent)
        return agents

    def _parallel_collaborate(self, agents: List[str], task: str) -> List[Dict]:
        """并行协作"""
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(agents)) as executor:
            futures = {}
            for agent_name in agents:
                future = executor.submit(self._call_agent, agent_name, task)
                futures[future] = agent_name

            for future in concurrent.futures.as_completed(futures):
                agent_name = futures[future]
                try:
                    result = future.result(timeout=30)
                    results.append(
                        {"agent": agent_name, "result": result, "success": True}
                    )
                except Exception as e:
                    results.append(
                        {"agent": agent_name, "error": str(e), "success": False}
                    )

        self.collaboration_history.append(
            {
                "task": task,
                "agents": agents,
                "results": results,
                "timestamp": __import__("time").time(),
            }
        )
        return results

    def _call_agent(self, agent_name: str, task: str) -> Dict:
        """调用Agent"""
        try:
            module = __import__(f"agents.{agent_name}.agent", fromlist=[agent_name])
            class_name = (
                "".join(w.capitalize() for w in agent_name.split("_")) + "Agent"
            )
            agent_class = getattr(module, class_name)
            agent = agent_class(self.user_id)
            return agent.process(task)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _delegate(self, agent_name: str, task: str) -> Dict:
        """委托单个Agent"""
        try:
            module = __import__(f"agents.{agent_name}.agent", fromlist=[agent_name])
            class_name = (
                "".join(w.capitalize() for w in agent_name.split("_")) + "Agent"
            )
            agent_class = getattr(module, class_name)
            agent = agent_class(self.user_id)
            result = agent.process(task)
            result["delegated_by"] = self.name
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "agent": self.name,
                "user_id": self.user_id,
            }

    def _fuse_results(self, results: List[Dict]) -> Dict:
        """融合结果"""
        success_results = [r for r in results if r.get("success")]
        if not success_results:
            return {"success": False, "response": "协作失败，没有Agent成功响应"}

        response = f"🤝 {len(success_results)}个Agent协作完成：\n"
        for r in success_results:
            agent = r.get("agent", "unknown")
            result = r.get("result", {})
            resp = result.get("response", "完成")[:100]
            response += f"• {agent}: {resp}\n"

        return {"success": True, "response": response, "fusion_type": "concat"}

    def _help(self) -> Dict:
        """帮助"""
        return {
            "success": True,
            "response": f"🤝 协作功能：\n• 自动识别：说「帮我分析数据并生成代码」\n• 支持Agent：{', '.join(set(self.AGENT_REGISTRY.keys()))}",
            "available_agents": list(set(self.AGENT_REGISTRY.keys())),
            "agent": self.name,
            "user_id": self.user_id,
        }
