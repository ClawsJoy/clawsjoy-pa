#!/usr/bin/env python3
"""Skill Evolver - Skill Evolver 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""技能进化器 - 自动生成、试错、总结、再学习"""
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.lib.closed_loop_config import closed_loop_config
from core.lib.memory_vector import vector_memory
from core.lib.skill_loader_v3 import skill_loader
from core.lib.smart_adapter import smart_adapter


class SkillEvolver:
    """技能进化器"""

    def __init__(self):
        self._load_config()
        self.evolution_history = []
        self.skill_templates = {}

    def _load_config(self):
        """从统一配置加载"""
        self.config = unified_config.get(
            "skill_evolver",
            {"generation": {}, "trial": {}, "learning": {}, "evolution": {}},
        )

    def generate_skill(self, task: str, experiences: List[Dict]) -> Optional[str]:
        """从经验生成原子技能"""
        # 提取成功经验和失败教训
        success_experiences = [e for e in experiences if e.get("success", False)]
        failure_lessons = [e for e in experiences if not e.get("success", False)]

        prompt = (
            self.config["generation"]
            .get("template", "")
            .format(
                task=task,
                success_experience=success_experiences[:3],
                failure_lessons=failure_lessons[:3],
            )
        )

        response = smart_adapter.generate(prompt, auto_select=True)

        # 解析生成的技能
        skill_code = self._parse_skill(response, task)

        if skill_code:
            return self._save_skill(skill_code, task)
        return None

    def _parse_skill(self, response: str, task: str) -> Optional[str]:
        """解析生成的技能代码"""
        # 提取技能名
        name_match = re.search(r"技能名:?\s*(\w+)", response)
        skill_name = (
            name_match.group(1) if name_match else f"auto_skill_{int(time.time())}"
        )

        # 提取描述
        desc_match = re.search(r"描述:?\s*(.+?)(?=\n\n|\n技能|$)", response, re.DOTALL)
        description = (
            desc_match.group(1).strip() if desc_match else f"自动生成的技能: {task}"
        )

        # 生成技能代码
        code = f'''# AUTO_GENERATED_SKILL
# 生成时间: {datetime.now().isoformat()}
# 原始任务: {task}

class {skill_name.capitalize()}Skill:
    name = "{skill_name}"
    description = "{description}"
    version = "1.0.0"
    category = "auto_generated"
    
    def execute(self, params):
        """执行技能"""
        goal = params.get("goal", "")
        if not goal:
            return {{"success": False, "error": "需要提供目标"}}

        # TODO: 实现具体逻辑
        # 这里是从经验中学习的逻辑

        return {{"success": True, "response": f"执行: {{goal}}"}}

skill = {skill_name.capitalize()}Skill()
'''
        return code

    def _save_skill(self, code: str, task: str) -> str:
        """保存生成的技能"""
        skills_dir = Path("skills/auto_generated")
        skills_dir.mkdir(exist_ok=True)

        # 提取技能名
        name_match = re.search(r'name = "(\w+)"', code)
        skill_name = name_match.group(1) if name_match else f"skill_{int(time.time())}"

        skill_file = skills_dir / f"{skill_name}.py"
        skill_file.write_text(code)

        return skill_name

    def trial(self, skill_name: str, test_cases: List[Dict]) -> Dict:
        """试错执行"""
        max_attempts = self.config["trial"].get("max_attempts", 3)
        results = []

        for i, test in enumerate(test_cases):
            for attempt in range(max_attempts):
                start = time.time()
                result = skill_loader.execute(skill_name, test.get("params", {}))
                elapsed = time.time() - start

                success = result.get("success", False)
                results.append(
                    {
                        "test_id": i,
                        "attempt": attempt + 1,
                        "success": success,
                        "result": result,
                        "time": elapsed,
                    }
                )

                if success:
                    break

                time.sleep(1)

        success_rate = sum(1 for r in results if r["success"]) / max(1, len(results))

        return {
            "skill_name": skill_name,
            "total_tests": len(results),
            "success_count": sum(1 for r in results if r["success"]),
            "success_rate": success_rate,
            "avg_time": sum(r["time"] for r in results) / max(1, len(results)),
            "results": results,
        }

    def summarize(self, skill_name: str, trial_result: Dict) -> Dict:
        """总结试错经验"""
        prompt = f"""
技能: {skill_name}
测试结果: 成功率 {trial_result['success_rate']:.0%}, 平均耗时 {trial_result['avg_time']:.2f}s
成功案例: {[r for r in trial_result['results'] if r['success']][:3]}
失败案例: {[r for r in trial_result['results'] if not r['success']][:3]}

请总结:
1. 技能的优势
2. 技能的不足
3. 改进建议
"""
        summary = smart_adapter.generate(prompt, auto_select=True)

        # 存储总结
        vector_memory.add(
            text=f"技能总结: {skill_name} | 成功率: {trial_result['success_rate']:.0%}",
            category="skill_summary",
            metadata={
                "skill": skill_name,
                "success_rate": trial_result["success_rate"],
            },
        )

        return {
            "skill_name": skill_name,
            "success_rate": trial_result["success_rate"],
            "summary": summary,
            "improvements": self._extract_improvements(summary),
        }

    def _extract_improvements(self, summary: str) -> List[str]:
        """提取改进建议"""
        improvements = []
        lines = summary.split("\n")
        for line in lines:
            if "改进" in line or "建议" in line or "优化" in line:
                improvements.append(line.strip())
        return improvements[:5]

    def evolve(self, skill_name: str, improvements: List[str]) -> Optional[str]:
        """根据改进建议进化技能"""
        # 获取原技能代码
        skill_file = Path(f"skills/auto_generated/{skill_name}.py")
        if not skill_file.exists():
            return None

        original_code = skill_file.read_text()

        prompt = f"""
原始技能代码:
{original_code}

改进建议:
{chr(10).join(improvements)}

请生成改进后的技能代码，保持相同接口。
"""
        new_code = smart_adapter.generate(prompt, auto_select=True)

        # 提取代码块
        code_match = re.search(r"```python\n(.*?)\n```", new_code, re.DOTALL)
        if code_match:
            new_code = code_match.group(1)

        # 更新版本
        new_code = new_code.replace(
            'version = "1.0.0"', f'version = "1.0.{len(self.evolution_history) + 1}"'
        )

        # 保存新版本
        backup_file = skill_file.with_suffix(
            f".v{len(self.evolution_history) + 1}.py.bak"
        )
        skill_file.rename(backup_file)
        skill_file.write_text(new_code)

        # 记录进化
        self.evolution_history.append(
            {
                "skill": skill_name,
                "timestamp": datetime.now().isoformat(),
                "version": len(self.evolution_history) + 1,
                "improvements": improvements,
            }
        )

        return skill_name

    def get_evolution_status(self, skill_name: str) -> Dict:
        """获取进化状态"""
        versions = list(Path("skills/auto_generated").glob(f"{skill_name}.v*.py.bak"))
        return {
            "skill": skill_name,
            "versions": len(versions) + 1,
            "evolution_history": [
                e for e in self.evolution_history if e["skill"] == skill_name
            ],
        }


skill_evolver = SkillEvolver()
