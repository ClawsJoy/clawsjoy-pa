#!/usr/bin/env python3
"""Learning Agent - Learning Agent 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""学习型 Agent - 从重复任务中学习"""

import sys

from core.lib.config_manager import config_manager
from core.lib.config_query import config_query
from core.lib.education.retrieval_generator import RetrievalGenerator
from core.lib.intent_learner import intent_handler


class LearningAgent:
    """学习型 Agent"""

    def __init__(self):
        self.config = config_query
        self.generator = RetrievalGenerator()

    def execute_task(self, task: str, params: dict = None) -> dict:
        """执行具体任务"""
        params = params or {}

        if task == "list_agents":
            return self._list_agents()
        elif task == "list_skills":
            return self._list_skills()
        elif task == "generate_chart":
            return self._generate_chart()
        else:
            return {"success": False, "error": f"未知任务: {task}"}

    def _list_agents(self) -> dict:
        agents = self.config.get_all_agents()
        result = [{"name": k, "display": v.get("name", k)} for k, v in agents.items()]
        return {
            "success": True,
            "task": "list_agents",
            "data": result,
            "count": len(result),
        }

    def _list_skills(self) -> dict:
        from pathlib import Path

        skills_dir = Path("unified_config.ROOT/skills")
        skills = [
            d.name
            for d in skills_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        ]
        return {
            "success": True,
            "task": "list_skills",
            "data": skills,
            "count": len(skills),
        }

    def _generate_chart(self) -> dict:
        svg = self.generator.generate_svg_content()
        from datetime import datetime
        from pathlib import Path

        filename = f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg"
        file_path = Path("unified_config.ROOT/output") / filename
        file_path.write_text(svg, encoding="utf-8")
        return {"success": True, "task": "generate_chart", "file_path": str(file_path)}

    def process(self, user_input: str) -> dict:
        """处理用户输入（带学习）"""

        # 1. 理解意图（学习优先）
        understanding = intent_handler.understand(user_input)

        # 2. 执行任务
        if understanding.get("task") != "unknown":
            result = self.execute_task(understanding["task"])

            # 3. 记录学习（成功时）
            if result.get("success"):
                intent_handler.record_feedback(
                    user_input,
                    understanding["task"],
                    True,
                    str(result.get("data", result.get("file_path", "")))[:200],
                )

            return {
                "success": True,
                "understanding": understanding,
                "result": result,
                "learned": understanding.get("source") == "learned",
            }

        return {
            "success": False,
            "message": "未能理解您的需求",
            "understanding": understanding,
        }


# learning_agent = LearningAgent()  # 注释：改为按需创建


if __name__ == "__main__":
    print("=" * 60)
    print("学习型 Agent 测试")
    print("=" * 60)

    # 第一次执行（LLM 理解）
    print("\n1. 第一次执行...")
    result = learning_agent.process("列出所有 Agent")
    print(f"   来源: {result['understanding'].get('source')}")
    print(f"   学习: {result.get('learned')}")

    # 第二次执行相同意图（应该从学习命中）
    print("\n2. 第二次执行相同意图...")
    result = learning_agent.process("有哪些 Agent")
    print(f"   来源: {result['understanding'].get('source')}")
    print(f"   学习: {result.get('learned')}")

    # 查看学习统计
    print("\n3. 学习统计:")
    stats = intent_handler.learner.get_stats()
    print(f"   已学习模式: {stats['total_patterns']}")
    print(f"   总交互: {stats['total_interactions']}")

    def compose_skills(self, requirement: str) -> Dict:
        """组合已有技能满足需求"""
        # 加载已有技能
        import json
        from pathlib import Path

        from core.lib.smart_adapter import smart_adapter

        skills_file = Path(f"{get_data_root()}/skill_registry_v2.json")
        if skills_file.exists():
            with open(skills_file, "r") as f:
                skills = json.load(f)
        else:
            skills = {}

        # 检索相关技能
        relevant = []
        for name, info in skills.items():
            if any(kw in name.lower() for kw in requirement.lower().split()[:3]):
                relevant.append(name)

        prompt = f"""需求：{requirement}
可用技能：{relevant[:10]}
请组合这些技能生成解决方案。"""

        solution = smart_adapter.generate(prompt, auto_select=True)

        return {
            "requirement": requirement,
            "skills_used": relevant[:5],
            "solution": solution[:500],
        }

    def compose_skills(self, requirement: str) -> Dict:
        """组合已有技能满足需求"""
        # 加载已有技能
        import json
        from pathlib import Path

        from core.lib.smart_adapter import smart_adapter

        skills_file = Path(f"{get_data_root()}/skill_registry_v2.json")
        if skills_file.exists():
            with open(skills_file, "r") as f:
                skills = json.load(f)
        else:
            skills = {}

        # 检索相关技能
        relevant = []
        for name, info in skills.items():
            if any(kw in name.lower() for kw in requirement.lower().split()[:3]):
                relevant.append(name)

        prompt = f"""需求：{requirement}
可用技能：{relevant[:10]}
请组合这些技能生成解决方案。"""

        solution = smart_adapter.generate(prompt, auto_select=True)

        return {
            "requirement": requirement,
            "skills_used": relevant[:5],
            "solution": solution[:500],
        }
