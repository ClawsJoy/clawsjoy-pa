#!/usr/bin/env python3
"""能力调度器 - Decision Agent + Orchestrator 协作"""

from typing import List, Dict, Any, Optional
from core.lib.capability_recommender import capability_recommender


class CapabilityScheduler:
    """统一能力调度器"""

    def __init__(self):
        self._decision_agent = None
        self._orchestrator = None

    def _get_decision_agent(self, user_id: str):
        """获取决策者 Agent"""
        if self._decision_agent is None:
            try:
                from core.agents.wisdom.wisdom_factory import wisdom_factory
                self._decision_agent = wisdom_factory.get_wisdom_agent("decision_agent", user_id)
            except:
                pass
        return self._decision_agent

    def _get_orchestrator(self, user_id: str):
        """获取编排器"""
        if self._orchestrator is None:
            try:
                from core.agents.wisdom.wisdom_factory import wisdom_factory
                self._orchestrator = wisdom_factory.get_wisdom_agent("orchestrator", user_id)
            except:
                pass
        return self._orchestrator

    def schedule(self, user_input: str, user_id: str = "default") -> Dict[str, Any]:
        """调度流程：LLM 推荐 → 决策者选择 → Orchestrator 执行"""
        
        # 1. LLM 推荐 Top 3
        candidates = capability_recommender.recommend_with_cache(user_input, n=3)
        print(f"[Scheduler] LLM 推荐: {[c.get('name') for c in candidates]}")

        if not candidates:
            return {
                "success": False,
                "error": "没有找到合适的能力",
                "recommendations": []
            }

        # 2. 决策者选择最佳
        decision_agent = self._get_decision_agent(user_id)
        if decision_agent and hasattr(decision_agent, 'select_best'):
            selected = decision_agent.select_best(candidates, user_input)
            print(f"[Scheduler] 决策者选择: {selected.get('name')}")
        else:
            selected = candidates[0]
            print(f"[Scheduler] 降级选择: {selected.get('name')}")

        # 3. 判断是否复杂任务
        orchestrator = self._get_orchestrator(user_id)
        if orchestrator:
            # 检查 Orchestrator 是否认为这是复杂任务
            task_type = self._detect_complexity(user_input)
            if task_type == "complex":
                print(f"[Scheduler] 复杂任务，交由 Orchestrator 处理")
                return orchestrator.process(user_input)

        # 4. 简单任务：直接执行
        return self._execute(selected, user_input, user_id)

    def _detect_complexity(self, user_input: str) -> str:
        """检测任务复杂度"""
        complex_keywords = ["并且", "同时", "然后", "之后", "接着", "先", "再", "最后"]
        action_words = ["分析", "生成", "发送", "创建", "写", "计算", "翻译"]
        
        if any(kw in user_input for kw in complex_keywords) or \
           sum(1 for aw in action_words if aw in user_input) >= 2:
            return "complex"
        return "simple"

    def _execute(self, capability: Dict, user_input: str, user_id: str) -> Dict:
        """执行选中的能力"""
        cap_type = capability.get('_type', 'unknown')
        cap_name = capability.get('name', '')

        if cap_type == 'agent':
            return self._execute_agent(cap_name, user_input, user_id)
        elif cap_type == 'skill':
            return self._execute_skill(cap_name, user_input, user_id)
        elif cap_type == 'tool':
            return self._execute_tool(cap_name, user_input, user_id)
        else:
            return {"success": False, "error": f"未知能力类型: {cap_type}"}

    def _execute_agent(self, agent_name: str, user_input: str, user_id: str) -> Dict:
        """执行 Agent"""
        try:
            from core.agents.wisdom.wisdom_factory import wisdom_factory
            agent = wisdom_factory.get_wisdom_agent(agent_name, user_id)
            if agent:
                return agent.process(user_input)
            return {"success": False, "error": f"Agent {agent_name} 不可用"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_skill(self, skill_name: str, user_input: str, user_id: str) -> Dict:
        """执行 Skill"""
        try:
            from core.lib.skill_registry_v6 import skill_registry
            params = {"input": user_input}
            result = skill_registry.execute_skill(skill_name, params)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_tool(self, tool_name: str, user_input: str, user_id: str) -> Dict:
        """执行 Tool"""
        return {"success": False, "error": f"工具 {tool_name} 执行待实现"}


# 全局实例
capability_scheduler = CapabilityScheduler()
