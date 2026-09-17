#!/usr/bin/env python3
"""Skill Chain - Skill Chain 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from typing import Dict, List


class SkillChainExecutor:
    """技能链执行器"""

    def execute_chain(self, steps: List[Dict], context: Dict = None) -> Dict:
        """执行技能链"""
        results = {}
        current_context = context or {}

        for i, step in enumerate(steps):
            skill_name = step.get("skill")
            params = step.get("params", {})

            # 替换参数中的上下文变量
            for key, value in params.items():
                if (
                    isinstance(value, str)
                    and value.startswith("{")
                    and value.endswith("}")
                ):
                    var_name = value[1:-1]
                    params[key] = current_context.get(var_name, value)

            # 执行技能
            from core.lib.skill_loader_v3 import skill_loader

            result = skill_loader.execute(skill_name, params)

            step_result = {"step": i, "skill": skill_name, "result": result}
            results[f"step_{i}"] = step_result
            current_context[f"step_{i}_result"] = result

        return {
            "success": all(
                r.get("result", {}).get("success", False) for r in results.values()
            ),
            "steps": results,
            "final_result": results.get(f"step_{len(steps)-1}", {}),
        }


skill_chain = SkillChainExecutor()
