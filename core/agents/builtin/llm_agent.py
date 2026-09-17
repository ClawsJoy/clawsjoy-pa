#!/usr/bin/env python3
"""Llm Agent - Llm Agent 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import logging

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""真正智能 Agent - 使用 LLM 理解意图"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

from core.lib.config_manager import config_manager


class LLMAgent:
    def __init__(self):
        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = config_manager.get_model()
        self.conversation_history = []

    def _call_llm(self, prompt: str) -> str:
        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 300},
                },
                timeout=config_manager.get_timeout("normal"),
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error: {e}", exc_info=True)
            print(f"LLM 调用失败: {e}")
        return ""

    def understand_intent(self, user_input: str) -> dict:
        """让 LLM 理解意图（真正的语义理解）"""

        prompt = f"""分析用户意图，返回 JSON。

用户说："{user_input}"

可选任务：
- system_intro: 询问系统是什么、介绍ClawsJoy
- list_agents: 询问有哪些Agent
- agent_detail: 询问某个Agent的职责
- list_skills: 询问有哪些技能
- generate_chart: 要求生成图表
- greeting: 打招呼
- unknown: 无法理解

返回格式：{{"task": "任务名", "entity": "实体名（如有）", "confidence": 0.0-1.0}}

只返回 JSON，不要解释。"""

        response = self._call_llm(prompt)

        try:
            # 提取 JSON
            import re

            match = re.search(r"\{[^{}]*\}", response)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error: {e}", exc_info=True)
            pass

        return {"task": "unknown", "confidence": 0.3}

    def execute(self, task: str, entity: str = None) -> str:
        """执行任务"""

        if task == "greeting":
            return "你好！我是 ClawsJoy 智能助手，有什么可以帮你的？"

        if task == "system_intro":
            return """ClawsJoy 是一个智能体操作系统，核心功能：
• 10个专业Agent协同工作
• 20+原子技能可调用
• 四层记忆系统（L0-L4）
• HTTPS + JWT 安全通信
• 用户数字分身和隐私保护"""

        if task == "list_agents":
            agents = [
                "决策Agent",
                "聊天Agent",
                "执行Agent",
                "采集Agent",
                "安全Agent",
                "分析Agent",
                "私人管家",
            ]
            return f"共有 {len(agents)} 个专业 Agent：{', '.join(agents)}"

        if task == "agent_detail":
            details = {
                "决策Agent": "决策Agent：用户总管，负责任务调度、技能编排、决策拍板",
                "聊天Agent": "聊天Agent：负责话术生成、用户沟通、自然语言交互",
                "执行Agent": "执行Agent：负责技能执行、任务运行、结果处理",
            }
            return details.get(entity, f"{entity}：负责相关工作")

        if task == "list_skills":
            skills_dir = Path("unified_config.ROOT/skills")
            skills = [
                d.name
                for d in skills_dir.iterdir()
                if d.is_dir() and not d.name.startswith("_")
            ]
            return f"共有 {len(skills)} 个原子技能：{', '.join(skills[:10])}" + (
                " 等" if len(skills) > 10 else ""
            )

        if task == "generate_chart":
            from core.lib.education.retrieval_generator import RetrievalGenerator

            gen = RetrievalGenerator()
            svg = gen.generate_svg_content()
            filename = f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg"
            file_path = Path("unified_config.ROOT/output") / filename
            file_path.write_text(svg, encoding="utf-8")
            return f"已生成架构图：{file_path}"

        return "抱歉，我没理解您的意思。试试问：ClawsJoy 是什么？、有哪些 Agent？"

    def process(self, user_input: str) -> dict:
        start = time.time()

        # 1. LLM 理解意图（真正智能）
        intent = self.understand_intent(user_input)
        task = intent.get("task", "unknown")
        entity = intent.get("entity")

        # 2. 执行任务
        response = self.execute(task, entity)

        # 3. 记录对话（用于上下文）
        self.conversation_history.append(
            {"user": user_input, "intent": task, "response": response[:100]}
        )
        if len(self.conversation_history) > 10:
            self.conversation_history.pop(0)

        elapsed = (time.time() - start) * 1000

        return {
            "response": response,
            "intent": task,
            "confidence": intent.get("confidence", 0),
            "time_ms": round(elapsed, 2),
        }


agent = LLMAgent()


if __name__ == "__main__":
    print("=" * 60)
    print("真正智能 Agent - 使用 LLM 理解语义")
    print("=" * 60)

    tests = [
        "你是谁",
        "这系统干嘛的",
        "ClawsJoy 有什么功能",
        "有哪些 Agent 啊",
        "决策Agent是做什么的",
        "你会不会生成图表",
        "来个架构图",
        "今天天气怎么样",
    ]

    for test in tests:
        print(f"\n👤 {test}")
        result = agent.process(test)
        print(f"🤖 {result['response']}")
        print(
            f"   [意图: {result['intent']}, 置信度: {result['confidence']}, 耗时: {result['time_ms']}ms]"
        )
