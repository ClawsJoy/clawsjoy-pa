"""Agent 编排引擎 - 多 Agent 协同工作流"""

import asyncio
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from engine.lib.logger import engine_logger


class OrchestrationEngine:
    """Agent 编排引擎"""

    def __init__(self):
        self.workflows = {}
        self.running_tasks = {}
        engine_logger.get().info("🔗 编排引擎已初始化")

    def create_workflow(self, name: str, steps: List[Dict]) -> Dict:
        """创建工作流"""
        self.workflows[name] = {
            "name": name,
            "steps": steps,
            "created_at": datetime.now().isoformat(),
            "status": "active",
        }
        return {"success": True, "workflow": name, "steps": len(steps)}

    def execute_workflow(self, name: str, context: Dict = None) -> Dict:
        """执行工作流"""
        if name not in self.workflows:
            return {"error": f"Workflow {name} not found"}

        workflow = self.workflows[name]
        results = []
        context = context or {}

        for step in workflow["steps"]:
            result = self._execute_step(step, context)
            results.append(result)
            if step.get("output_key"):
                context[step["output_key"]] = result.get("result")

        return {
            "success": True,
            "workflow": name,
            "results": results,
            "context": context,
        }

    def _execute_step(self, step: Dict, context: Dict) -> Dict:
        """执行单个步骤"""
        agent_name = step.get("agent")
        action = step.get("action", "process")
        params = step.get("params", {})

        # 替换模板变量
        for key, value in params.items():
            if isinstance(value, str) and "{{" in value:
                for var, val in context.items():
                    value = value.replace(f"{{{{{var}}}}}", str(val))
                params[key] = value

        # 调用 Agent
        try:
            from engine import engine

            if agent_name == "code_agent":
                result = engine.skill.execute_skill("code_agent", params)
            elif agent_name == "translate_agent":
                result = engine.skill.execute_skill("translate_agent", params)
            else:
                result = {"success": True, "result": "executed"}

            return {
                "step": step.get("name", agent_name),
                "agent": agent_name,
                "success": result.get("success", True),
                "result": result.get("result", result),
            }
        except Exception as e:
            return {
                "step": step.get("name", agent_name),
                "agent": agent_name,
                "success": False,
                "error": str(e),
            }

    def orchestrate(self, task: str, agents: List[str] = None) -> Dict:
        """编排多 Agent 协同"""
        if not agents:
            agents = ["code_agent", "translate_agent"]

        results = {}
        for agent in agents:
            try:
                from engine import engine

                result = engine.skill.execute_skill(agent, {"task": task})
                results[agent] = result
            except Exception as e:
                results[agent] = {"error": str(e)}

        return {"success": True, "task": task, "agents": agents, "results": results}

    def process(self, input_data: Any = None, **kwargs) -> Any:
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, str):
            return self.orchestrate(input_data, kwargs.get("agents"))
        if isinstance(input_data, dict):
            action = input_data.get("action", "orchestrate")
            if action == "orchestrate":
                return self.orchestrate(
                    input_data.get("task", ""), input_data.get("agents")
                )
            elif action == "workflow":
                return self.execute_workflow(
                    input_data.get("name", ""), input_data.get("context")
                )
        return self.get_stats()

    def get_stats(self) -> Dict:
        return {
            "workflows": len(self.workflows),
            "running_tasks": len(self.running_tasks),
            "status": "active",
        }

    def reload(self) -> Dict:
        return {"success": True, "message": "Orchestration engine reloaded"}

    def health_check(self) -> Dict:
        return {"name": "orchestration_engine", "status": "healthy"}


orchestration_engine = OrchestrationEngine()
