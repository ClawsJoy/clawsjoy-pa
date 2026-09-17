#!/usr/bin/env python3
"""Trial Agent - Trial Agent 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.lib.skill_loader_v3 import skill_loader
from core.lib.smart_adapter import smart_adapter


class TrialAgent:
    """
    试错智能体

    核心能力:
    1. 分析拆解任务
    2. 制定执行计划
    3. 执行并评估结果
    4. 失败时调整策略重试
    5. 记录学习经验
    """

    name = "trial_agent"
    version = "1.0.0"

    def __init__(self):
        self.max_attempts = 3
        self.learning_file = Path("data/agent_learning.json")
        self.experiences = self._load_experiences()

    def _load_experiences(self) -> Dict:
        """加载历史经验"""
        if self.learning_file.exists():
            import json

            with open(self.learning_file, "r") as f:
                return json.load(f)
        return {"successful_plans": [], "failed_patterns": []}

    def _save_experiences(self):
        """保存经验"""
        import json

        with open(self.learning_file, "w") as f:
            json.dump(self.experiences, f, indent=2)

    def execute(self, goal: str, context: Dict = None) -> Dict:
        """执行任务（试错循环）"""
        print(f"\n🤖 [试错智能体] 开始处理: {goal[:80]}")

        for attempt in range(1, self.max_attempts + 1):
            print(f"\n📌 尝试 #{attempt}")

            # 1. 分析拆解
            analysis = self._analyze(goal, attempt)
            if not analysis.get("success"):
                continue

            # 2. 制定计划
            plan = self._plan(analysis, attempt)
            if not plan.get("steps"):
                continue

            # 3. 执行计划
            result = self._execute_plan(plan, goal, attempt)

            # 4. 评估结果
            evaluation = self._evaluate(result, goal)

            if evaluation.get("satisfactory"):
                # 成功！记录经验
                self._learn(goal, plan, result, attempt)
                return {
                    "success": True,
                    "result": result.get("final_output"),
                    "attempts": attempt,
                    "plan": plan.get("steps"),
                    "learned": True,
                }
            else:
                # 失败，调整策略
                print(f"⚠️ 尝试 #{attempt} 失败: {evaluation.get('reason')}")
                self._adjust_strategy(goal, plan, result, attempt)

        return {
            "success": False,
            "error": f"经过 {self.max_attempts} 次尝试仍未成功",
            "attempts": self.max_attempts,
        }

    def _analyze(self, goal: str, attempt: int) -> Dict:
        """分析任务"""
        # 从经验中查找相似任务
        similar = self._find_similar_experience(goal)

        prompt = f"""分析以下用户目标，拆解为子任务。

用户目标: {goal}

{"历史成功经验:" + str(similar) if similar else ""}

输出JSON格式:
{{
  "subtasks": ["子任务1", "子任务2", ...],
  "required_skills": ["技能1", "技能2", ...],
  "estimated_steps": 数量,
  "difficulty": "简单/中等/复杂"
}}"""

        response = smart_adapter.generate(prompt, auto_select=True)
        import re

        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"success": False}

    def _plan(self, analysis: Dict, attempt: int) -> Dict:
        """制定执行计划"""
        required_skills = analysis.get("required_skills", [])

        # 获取可用技能
        available_skills = skill_loader.list_skills()

        # 匹配技能
        matched_skills = []
        for req in required_skills:
            for skill in available_skills:
                if req.lower() in skill.lower() or skill.lower() in req.lower():
                    matched_skills.append(skill)
                    break

        if not matched_skills:
            # 没有匹配的技能，使用通用执行器
            matched_skills = ["llm"]

        plan = {
            "steps": [
                {"skill": s, "params": {"goal": analysis.get("original_goal", "")}}
                for s in matched_skills
            ],
            "attempt": attempt,
        }

        return plan

    def _execute_plan(self, plan: Dict, goal: str, attempt: int) -> Dict:
        """执行计划"""
        steps = plan.get("steps", [])
        results = []

        for i, step in enumerate(steps):
            skill_name = step.get("skill")
            params = step.get("params", {})

            print(f"  执行步骤 {i+1}: {skill_name}")

            result = skill_loader.execute(skill_name, params)
            results.append(result)

            if not result.get("success"):
                return {
                    "success": False,
                    "failed_step": i + 1,
                    "partial_results": results,
                }

            time.sleep(0.5)  # 避免过载

        final_output = results[-1].get("result", results[-1]) if results else None

        return {
            "success": True,
            "results": results,
            "final_output": final_output,
            "steps_executed": len(steps),
        }

    def _evaluate(self, result: Dict, goal: str) -> Dict:
        """评估执行结果"""
        if not result.get("success"):
            return {"satisfactory": False, "reason": "执行失败"}

        final_output = result.get("final_output", "")

        prompt = f"""评估以下结果是否满足用户需求。

用户需求: {goal}
执行结果: {str(final_output)[:500]}

输出JSON:
{{
  "satisfactory": true/false,
  "score": 0-100,
  "reason": "评估理由"
}}"""

        response = smart_adapter.generate(prompt, auto_select=True)
        import re

        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            return json.loads(match.group())

        return {"satisfactory": len(str(final_output)) > 50, "score": 60}

    def _adjust_strategy(self, goal: str, plan: Dict, result: Dict, attempt: int):
        """调整策略"""
        print(f"🔄 调整策略，准备第 {attempt + 1} 次尝试")
        # TODO: 根据失败原因调整计划

    def _find_similar_experience(self, goal: str) -> Dict:
        """查找相似经验"""
        for exp in self.experiences.get("successful_plans", []):
            if any(kw in goal for kw in exp.get("keywords", [])):
                return exp
        return {}

    def _learn(self, goal: str, plan: Dict, result: Dict, attempt: int):
        """学习成功经验"""
        experience = {
            "goal": goal[:100],
            "keywords": [w for w in goal.split() if len(w) > 2][:5],
            "plan": plan.get("steps", []),
            "attempts": attempt,
            "timestamp": datetime.now().isoformat(),
        }

        self.experiences["successful_plans"].append(experience)
        # 保留最近100条
        self.experiences["successful_plans"] = self.experiences["successful_plans"][
            -100:
        ]
        self._save_experiences()

        print(f"📚 学习成功经验: {experience['goal'][:50]}...")


# trial_agent = TrialAgent()  # 注释：改为按需创建
