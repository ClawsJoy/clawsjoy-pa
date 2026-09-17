#!/usr/bin/env python3
"""Skill Chain Executor - Skill Chain Executor 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from pathlib import Path
from typing import Any, Dict, List

import yaml


class SkillChainExecutor:
    """技能链执行器"""

    def __init__(self):
        self.workflow_dir = Path("config/workflows")
        self.workflow_dir.mkdir(parents=True, exist_ok=True)

    def execute_workflow(self, workflow_name: str, params: Dict) -> Dict:
        """执行工作流"""
        # 加载工作流定义
        workflow_file = self.workflow_dir / f"{workflow_name}.yaml"
        if not workflow_file.exists():
            return {"success": False, "error": f"工作流不存在: {workflow_name}"}

        with open(workflow_file, "r") as f:
            workflow = yaml.safe_load(f)

        print(f"🚀 执行工作流: {workflow.get('name', workflow_name)}")

        # 执行步骤
        context = params.copy()
        steps = workflow.get("steps", [])

        for i, step in enumerate(steps):
            skill_name = step.get("skill")
            step_params = step.get("params", {}).copy()

            # 替换参数中的上下文变量
            for key, value in step_params.items():
                if (
                    isinstance(value, str)
                    and value.startswith("{")
                    and value.endswith("}")
                ):
                    var_name = value[1:-1]
                    # 支持嵌套访问，如 {description.result}
                    parts = var_name.split(".")
                    current = context
                    for part in parts:
                        if isinstance(current, dict):
                            current = current.get(part)
                        else:
                            current = None
                            break
                    step_params[key] = current if current is not None else value

            print(f"  步骤 {i+1}: {skill_name}")

            # 执行技能
            from core.lib.skill_loader_v3 import skill_loader

            result = skill_loader.execute(skill_name, step_params)

            # 存储结果到上下文
            output_key = step.get("output", f"step_{i}_result")
            context[output_key] = result

            if not result.get("success", False):
                return {
                    "success": False,
                    "error": f"步骤 {i+1} 失败: {result.get('error', '未知错误')}",
                    "step": i + 1,
                    "skill": skill_name,
                }

        # 返回最终结果
        output_template = workflow.get("output", "{final_result}")
        final_result = self._format_output(output_template, context)

        return {
            "success": True,
            "result": final_result,
            "steps": len(steps),
            "workflow": workflow_name,
        }

    def _format_output(self, template: str, context: Dict) -> str:
        """格式化输出"""
        import re

        pattern = r"\{([^}]+)\}"

        def replace(match):
            var_name = match.group(1)
            parts = var_name.split(".")
            current = context
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return match.group(0)
            return str(current) if current is not None else match.group(0)

        return re.sub(pattern, replace, template)


# 全局实例
skill_chain = SkillChainExecutor()
