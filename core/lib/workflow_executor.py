#!/usr/bin/env python3
"""Workflow Executor - Agent 工作流执行器

@version: 2.0.0
@author: ClawsJoy
@date: 2026-5-31
@enhanced: 完整实现工作流执行、步骤依赖、变量传递、错误处理
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class WorkflowExecutor:
    """工作流执行器 - 执行多 Agent 协作工作流"""

    def __init__(self, workflows_dir: str = "config/workflows"):
        self.workflows_dir = Path(workflows_dir)
        self._workflows = {}
        self._load_all()

    def _load_all(self):
        """加载所有工作流模板"""
        if not self.workflows_dir.exists():
            return

        for f in self.workflows_dir.glob("*.yaml"):
            try:
                with open(f, "r") as fp:
                    self._workflows[f.stem] = yaml.safe_load(fp)
            except Exception as e:
                print(f"⚠️ 加载工作流失败 {f.name}: {e}")

    def reload(self):
        """热重载工作流配置"""
        self._workflows.clear()
        self._load_all()
        return {"success": True, "loaded": len(self._workflows)}

    def list_workflows(self) -> List[Dict]:
        """列出所有工作流"""
        return [
            {
                "name": name,
                "description": wf.get("description", ""),
                "version": wf.get("version", "1.0"),
            }
            for name, wf in self._workflows.items()
        ]

    def get_workflow(self, name: str) -> Optional[Dict]:
        """获取工作流定义"""
        return self._workflows.get(name)

    def execute(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工作流

        Args:
            name: 工作流名称
            params: 输入参数

        Returns:
            {"success": True, "results": {...}, "execution_id": "..."}
        """
        workflow = self._workflows.get(name)
        if not workflow:
            return {"success": False, "error": f"工作流不存在: {name}"}

        execution_id = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        results = {}
        step_results = {}

        print(f"🚀 执行工作流: {workflow.get('name', name)} (ID: {execution_id})")

        for step in workflow.get("steps", []):
            step_name = step.get("name")
            agent = step.get("agent")
            prompt_template = step.get("prompt", "")
            output_key = step.get("output")
            optional = step.get("optional", False)

            # 渲染 prompt（替换变量）
            prompt = prompt_template
            for key, value in {**params, **step_results}.items():
                prompt = prompt.replace(f"{{{key}}}", str(value))

            print(f"  📍 步骤: {step_name} → {agent}")

            # 调用 Agent
            result = self._call_agent(agent, prompt)

            if result.get("success"):
                if output_key:
                    step_results[output_key] = result.get("response", result)
                    results[output_key] = result.get("response", result)
                print(f"     ✅ 完成")
            else:
                error_msg = result.get("error", "未知错误")
                if optional:
                    print(f"     ⚠️ 可选步骤失败: {error_msg}")
                    continue
                else:
                    print(f"     ❌ 失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "step": step_name,
                        "execution_id": execution_id,
                    }

        return {
            "success": True,
            "results": results,
            "execution_id": execution_id,
            "workflow": name,
        }

    def _call_agent(self, agent_name: str, prompt: str) -> Dict:
        """调用 Agent"""
        try:
            # 动态导入 Agent
            module_name = f"core.agents.builtin.{agent_name}"
            module = __import__(module_name, fromlist=[agent_name])

            # 获取 Agent 类
            class_name = "".join(word.capitalize() for word in agent_name.split("_"))
            agent_class = getattr(module, class_name)
            agent = agent_class("workflow")

            # 调用 process
            result = agent.process(prompt)
            return {"success": True, "response": result.get("response", str(result))}
        except ImportError:
            # 尝试另一种命名
            try:
                from core.agents.builtin.orchestrator import orchestrator

                result = orchestrator.dispatch(prompt, agent_name)
                if result.get("success"):
                    return {
                        "success": True,
                        "response": result.get("result", "处理完成"),
                    }
                return {
                    "success": False,
                    "error": result.get("error", "Agent 调用失败"),
                }
            except Exception as e:
                return {"success": False, "error": f"Agent 调用失败: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# 全局实例
workflow_executor = WorkflowExecutor()
