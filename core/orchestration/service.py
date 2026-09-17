"""独立编排服务 - 不依赖 Orchestrator"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict

from core.orchestration.config_planner import config_planner
from core.orchestration.planner import TaskPlanner
from engine.orchestration.task_manager import task_manager


class OrchestrationService:
    """独立编排服务"""

    def __init__(self):
        self.task_manager = task_manager
        self.planner = config_planner
        self.dag_planner = TaskPlanner()

    def execute(self, user_input: str, user_id: str = "default", dag: bool = False) -> Dict:
        # audit 类型：走并行调度（plan_dag() 拆解为只读审计子任务 → 并行调度器执行 → 结果并表）
        if not dag and self._is_audit(user_input):
            return self._execute_audit(user_input, user_id)

        # dag=True 时走并行路径：调用 planner.plan_dag() 生成带 parallel_group 的 DAG 任务
        if dag:
            return self.execute_dag(user_input, user_id)

        tasks = self.planner.create_tasks(user_input)
        if not tasks:
            return {"success": False, "error": "无法生成任务计划"}

        formatted_tasks = []
        for task in tasks:
            formatted_tasks.append(
                {
                    "name": task.get("name"),
                    "agent": task.get("agent"),
                    "params": task.get("params", {}),
                    "depends_on": task.get("depends_on", []),
                    "optional": task.get("optional", False),
                    "parallel_group": task.get("parallel_group"),
                }
            )

        plan = self.task_manager.create_plan(name="编排任务", description=user_input[:100], tasks=formatted_tasks)

        def get_agent(agent_name: str):
            return self._get_agent(agent_name, user_id)

        result = self.task_manager.execute_plan_parallel(plan.id, get_agent)

        return {
            "success": result.get("success", False),
            "plan_id": plan.id,
            "results": result.get("results", []),
        }

    @staticmethod
    def _is_audit(user_input: str) -> bool:
        """检测 audit 类型：审计任务只做只读操作，走并行调度"""
        if isinstance(user_input, dict):
            user_input = str(user_input.get("message", ""))
        text = str(user_input)
        return "审计" in text or "audit" in text.lower()

    def _execute_audit(self, user_input: str, user_id: str) -> Dict:
        """audit 类型入口：plan_dag() 拆解为只读审计子任务 → 并行调度器执行 → 结果并表"""
        result = self.execute_dag(user_input, user_id)
        if not result.get("success"):
            return result
        result["audit"] = True
        result["summary"] = "\n".join(
            "[{}] {}".format(r.get("task"), (r.get("response") or "")[:200]) for r in result.get("results", [])
        )
        return result

    def execute_dag(self, user_input: str, user_id: str = "default") -> Dict:
        """DAG 并行路径：plan_dag() 拆解任务（含 parallel_group），交由并行调度器执行"""
        plan_data = self.dag_planner.plan_dag(user_input)
        if not plan_data.get("success"):
            return {"success": False, "error": plan_data.get("error", "DAG 规划失败")}

        formatted_tasks = []
        for task in plan_data.get("tasks", []):
            formatted_tasks.append(
                {
                    "name": task.get("name"),
                    "agent": task.get("agent"),
                    "action": task.get("action", "handle"),
                    "params": {"message": task.get("message", "")},
                    "depends_on": task.get("depends_on", []),
                    "optional": task.get("optional", False),
                    "parallel_group": task.get("parallel_group"),
                }
            )

        plan = self.task_manager.create_plan(name="DAG 编排任务", description=user_input[:100], tasks=formatted_tasks)

        def get_agent(agent_name: str):
            return self._get_agent(agent_name, user_id)

        result = self.task_manager.execute_plan_parallel(plan.id, get_agent)

        return {
            "success": result.get("success", False),
            "plan_id": plan.id,
            "dag": True,
            "results": result.get("results", []),
        }

    def _get_agent(self, agent_name: str, user_id: str):
        try:
            if agent_name == "video_agent":
                from agents.video_agent.agent_v4 import VideoAgentV4 as VideoAgent

                return VideoAgent(user_id)
            elif agent_name == "vision_agent":
                from agents.vision_agent.agent import VisionAgent

                return VisionAgent(user_id)
            elif agent_name == "writer_agent":
                from agents.writer_agent.agent import WriterAgent

                return WriterAgent(user_id)
            elif agent_name == "analysis_agent":
                from agents.analysis_agent.agent_v4 import AnalysisAgentV4 as AnalysisAgent

                return AnalysisAgent(user_id)
            else:
                from agents.chat_agent.agent import ChatAgent

                return ChatAgent(user_id)
        except Exception as e:
            print(f"获取 Agent {agent_name} 失败: {e}")
            return None


orchestration_service = OrchestrationService()


if __name__ == "__main__":
    result = orchestration_service.execute("帮我制作一个关于AI的视频")
    print(f"成功: {result.get('success')}")
    for r in result.get("results", []):
        print(f"  {r.get('task')}: {r.get('response', '')[:50]}")
