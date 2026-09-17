#!/usr/bin/env python3
"""Real Agent - Real Agent 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""真正的智能 Agent - 完整版"""

import sys
import time
from datetime import datetime
from pathlib import Path

from core.lib.config_manager import config_manager
from core.lib.config_query import config_query
from core.lib.real_learner import real_learner


class RealAgent:
    def __init__(self):
        self.config = config_query
        self.agent_details = {
            "decision_agent": "决策Agent：用户总管，负责任务调度、技能编排、决策拍板",
            "chat_agent": "聊天Agent：负责话术生成、用户沟通、自然语言交互",
            "executor_agent": "执行Agent：负责技能执行、任务运行、结果处理",
            "collector_agent": "采集Agent：负责参数收集、信息采集、上下文管理",
            "security_agent": "安全Agent：负责安全检查、权限验证、审计日志",
            "analysis_agent": "分析Agent：负责数据分析、优化建议、系统监控",
            "personal_butler": "私人管家：用户的数字分身，1对1专属服务",
            "memory_manager": "记忆Agent：负责记忆存储、回忆、向量搜索",
            "orchestrator": "编排Agent：负责任务规划、工作流管理",
            "code_agent": "代码Agent：负责代码生成、审查、调试",
        }

    def execute(self, task: str, params: dict = None) -> dict:
        params = params or {}

        if task == "list_agents":
            agents = self.config.get_all_agents()
            result = [
                {"name": k, "display": v.get("name", k)} for k, v in agents.items()
            ]
            return {"success": True, "data": result, "count": len(result)}

        elif task == "agent_detail":
            agent_name = params.get("agent_name", "")
            for key, detail in self.agent_details.items():
                if agent_name in key or key in agent_name:
                    return {"success": True, "data": detail, "agent": key}
            return {"success": False, "error": f"未找到 Agent: {agent_name}"}

        elif task == "list_skills":
            skills_dir = Path("unified_config.ROOT/skills")
            skills = [
                d.name
                for d in skills_dir.iterdir()
                if d.is_dir() and not d.name.startswith("_")
            ]
            return {"success": True, "data": skills[:20], "count": len(skills)}

        elif task == "system_intro":
            intro = """ClawsJoy 是一个智能体操作系统，核心功能：
- 10个专业Agent协同工作
- 20+原子技能可调用
- 四层记忆系统（L0-L4）
- HTTPS + JWT 安全通信
- 用户数字分身和隐私保护
- 配置驱动架构"""
            return {"success": True, "data": intro}

        elif task == "generate_chart":
            from core.lib.education.retrieval_generator import RetrievalGenerator

            gen = RetrievalGenerator()
            svg = gen.generate_svg_content()
            filename = f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg"
            file_path = Path("unified_config.ROOT/output") / filename
            file_path.write_text(svg, encoding="utf-8")
            return {"success": True, "file_path": str(file_path)}

        else:
            return {"success": False, "error": f"未知任务: {task}"}

    def process(self, user_input: str) -> dict:
        start_time = time.time()
        cache_key = user_input.lower().strip()

        # 查缓存
        cached = real_learner.get_cached(cache_key)
        if cached:
            response_time = time.time() - start_time
            real_learner.record_request(
                user_input,
                cached.get("task", "cached"),
                response_time,
                True,
                cache_hit=True,
            )
            return {
                "success": True,
                "result": cached.get("result"),
                "cached": True,
                "response_time_ms": round(response_time * 1000, 2),
            }

        # 意图识别
        lower = user_input.lower()
        task = "unknown"
        params = {}

        if "agent" in lower and (
            "有哪些" in lower or "列表" in lower or "list" in lower
        ):
            task = "list_agents"
        elif "介绍" in lower or "是什么" in lower:
            if "clawsjoy" in lower or "系统" in lower:
                task = "system_intro"
            elif "agent" in lower:
                task = "agent_detail"
                # 提取 Agent 名称
                for agent in self.agent_details.keys():
                    if agent.replace("_", "") in lower.replace("_", ""):
                        params["agent_name"] = agent
                        break
        elif "技能" in lower or "skill" in lower:
            task = "list_skills"
        elif "图" in lower:
            task = "generate_chart"
        elif any(g in lower for g in ["你好", "hi", "hello", "嗨"]):
            task = "greeting"

        # 执行
        result = self.execute(task, params)
        response_time = time.time() - start_time

        # 记录
        real_learner.record_request(
            user_input, task, response_time, result.get("success", False)
        )

        # 缓存
        if result.get("success"):
            real_learner.cache_result(cache_key, {"task": task, "result": result})

        return {
            "success": result.get("success", False),
            "result": result.get("data", result.get("file_path", result.get("error"))),
            "task": task,
            "cached": False,
            "response_time_ms": round(response_time * 1000, 2),
        }


# real_agent = RealAgent()  # 注释：改为按需创建


if __name__ == "__main__":
    print("真正智能 Agent 测试")
    print("=" * 50)

    tests = [
        "clawsjoy系统是什么",
        "ClawsJoy 有哪些 Agent？",
        "决策Agent是干什么的？",
        "它和聊天Agent有什么区别？",
        "有哪些技能",
        "生成一张架构图",
    ]

    for test in tests:
        print(f"\n用户: {test}")
        result = real_agent.process(test)
        if result.get("success"):
            output = result.get("result")
            if isinstance(output, list):
                output = f"找到 {len(output)} 项"
            print(f"系统: {output[:100]}")
        else:
            print(f"系统: 未理解")
        print(f"耗时: {result.get('response_time_ms')}ms, 任务: {result.get('task')}")
