#!/usr/bin/env python3
"""导演智能体 - 增强版（复杂工作流编排、条件分支、循环）"""

import re
import time
from typing import Any, Dict, List, Optional

from core.agents.business.base_business_agent import BusinessAgent


class DirectorAgent(BusinessAgent):
    name = "director_agent"
    description = "任务导演与编排"
    version = "3.0.0"

    # 预定义工作流模板
    WORKFLOW_TEMPLATES = {
        "内容创作": [
            {
                "step": 1,
                "name": "主题分析",
                "agent": "analysis_agent",
                "action": "分析主题",
            },
            {
                "step": 2,
                "name": "内容创作",
                "agent": "writer_agent",
                "action": "写文章",
            },
            {"step": 3, "name": "优化润色", "agent": "writer_agent", "action": "润色"},
            {"step": 4, "name": "总结", "agent": "chat_agent", "action": "总结"},
        ],
        "数据分析": [
            {
                "step": 1,
                "name": "数据收集",
                "agent": "analysis_agent",
                "action": "收集数据",
            },
            {
                "step": 2,
                "name": "数据分析",
                "agent": "analysis_agent",
                "action": "分析",
            },
            {
                "step": 3,
                "name": "决策建议",
                "agent": "decision_agent",
                "action": "决策",
            },
            {"step": 4, "name": "执行", "agent": "executor_agent", "action": "执行"},
        ],
        "视频制作": [
            {
                "step": 1,
                "name": "脚本生成",
                "agent": "youtube_agent",
                "action": "生成脚本",
            },
            {"step": 2, "name": "视频处理", "agent": "video_agent", "action": "处理"},
            {
                "step": 3,
                "name": "字幕添加",
                "agent": "video_agent",
                "action": "添加字幕",
            },
            {"step": 4, "name": "发布", "agent": "youtube_agent", "action": "发布"},
        ],
    }

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.workflow_history = []
        print(f"🎬 导演智能体 v3.0 已上线")

    def _execute_business(self, user_input: str, context: dict = None) -> dict:
        """业务逻辑实现 - BusinessAgent 要求"""
        return self.process(user_input, context)

    def process(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        print(f"[导演] 收到: {user_input}")

        # 1. 识别工作流类型
        workflow_type = self._identify_workflow(user_input)

        if workflow_type:
            workflow = self.WORKFLOW_TEMPLATES.get(workflow_type)
            if workflow:
                results = self._execute_workflow(workflow, user_input)
                return self._workflow_response(results, workflow_type)

        # 2. 自定义工作流
        if "工作流" in user_input or "流程" in user_input:
            workflow = self._parse_custom_workflow(user_input)
            if workflow:
                results = self._execute_workflow(workflow, user_input)
                return self._workflow_response(results, "自定义")

        return self._help()

    def _identify_workflow(self, text: str) -> Optional[str]:
        """识别工作流类型"""
        for wf_type in self.WORKFLOW_TEMPLATES:
            if wf_type in text:
                return wf_type
        return None

    def _parse_custom_workflow(self, text: str) -> List[Dict]:
        """解析自定义工作流"""
        workflow = []
        steps = re.findall(r"(\d+)\.\s*(\w+)\s*->\s*(\w+)", text)
        if steps:
            for step_num, agent, action in steps:
                workflow.append(
                    {
                        "step": int(step_num),
                        "name": f"步骤{step_num}",
                        "agent": f"{agent}_agent",
                        "action": action,
                    }
                )
        return workflow

    def _execute_workflow(self, workflow: List[Dict], context: str) -> List[Dict]:
        """执行工作流"""
        results = []
        results_map = {}

        for step in workflow:
            agent_name = step.get("agent")
            action = step.get("action")

            # 检查依赖
            deps = step.get("deps", [])
            deps_satisfied = all(dep in results_map for dep in deps)

            if not deps_satisfied:
                results.append(
                    {
                        "step": step.get("step"),
                        "name": step.get("name"),
                        "status": "skipped",
                        "reason": "依赖未满足",
                    }
                )
                continue

            # 执行步骤
            start_time = time.time()
            try:
                module = __import__(f"agents.{agent_name}.agent", fromlist=[agent_name])
                class_name = (
                    "".join(w.capitalize() for w in agent_name.split("_")) + "Agent"
                )
                agent_class = getattr(module, class_name)
                agent = agent_class(self.user_id)

                # 使用上一步结果作为上下文
                step_context = {**results_map, "current_action": action}
                result = agent.process(action, step_context)

                duration = (time.time() - start_time) * 1000
                results_map[step.get("name")] = result

                results.append(
                    {
                        "step": step.get("step"),
                        "name": step.get("name"),
                        "agent": agent_name,
                        "action": action,
                        "status": "success",
                        "duration_ms": round(duration, 2),
                        "result": result.get("response", "")[:200],
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "step": step.get("step"),
                        "name": step.get("name"),
                        "agent": agent_name,
                        "action": action,
                        "status": "failed",
                        "error": str(e),
                    }
                )

        self.workflow_history.append(
            {"workflow": workflow, "results": results, "timestamp": time.time()}
        )
        return results

    def _workflow_response(self, results: List[Dict], workflow_type: str) -> Dict:
        """构建工作流响应"""
        success_count = len([r for r in results if r.get("status") == "success"])
        failed_count = len([r for r in results if r.get("status") == "failed"])

        response = f"🎬 {workflow_type}工作流执行完成\n"
        response += f"📊 统计：成功 {success_count} 步，失败 {failed_count} 步\n\n"

        for r in results:
            status_icon = "✅" if r.get("status") == "success" else "❌"
            response += f"{status_icon} 步骤{r.get('step')}: {r.get('name')}\n"
            if r.get("duration_ms"):
                response += f"   ⏱️ {r.get('duration_ms')}ms\n"

        return {
            "success": True,
            "response": response,
            "workflow_type": workflow_type,
            "results": results,
            "agent": self.name,
            "user_id": self.user_id,
        }

    def _help(self) -> Dict:
        """帮助"""
        return {
            "success": True,
            "response": f"🎬 导演功能：\n• 内容创作工作流\n• 数据分析工作流\n• 视频制作工作流\n支持的工作流：{', '.join(self.WORKFLOW_TEMPLATES.keys())}",
            "workflows": list(self.WORKFLOW_TEMPLATES.keys()),
            "agent": self.name,
            "user_id": self.user_id,
        }
