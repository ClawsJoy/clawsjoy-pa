#!/usr/bin/env python3
"""Structured Generator - Structured Generator 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""结构化生成器 - 约束 LLM 输出格式，但允许自由填充内容"""

import json
from pathlib import Path
from typing import Any, Dict

import requests


class StructuredGenerator:
    """约束 LLM 输出格式，同时保持内容灵活性"""

    def __init__(self):
        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = unified_config.get_llm_config().get(
            "fast_model",
            unified_config.get_llm_config().get(
                "fast_model",
                unified_config.get(
                    "llm.fast_model", config_helper.get_llm_model(fast=True)
                ),
            ),
        )

    def generate_with_schema(self, prompt: str, output_schema: Dict) -> Dict:
        """按照 schema 生成结构化输出"""

        schema_str = json.dumps(output_schema, indent=2, ensure_ascii=False)

        full_prompt = f"""你是一个智能助手，需要按照指定的 JSON 格式回答问题。

输出格式要求：
{schema_str}

用户问题：{prompt}

请严格按照上述 JSON 格式输出，不要添加任何额外内容。
每个字段的内容要详细、具体、有信息量。"""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"num_predict": 1500},
                },
                timeout=config_helper.get_timeout("llm"),
            )
            if resp.status_code == 200:
                response = resp.json().get("response", "")
                # 提取 JSON
                import re

                match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
                if match:
                    return json.loads(match.group())
        except Exception as e:
            print(f"生成失败: {e}")

        return {}

    def generate_agent_description(self) -> Dict:
        """生成 Agent 描述"""
        schema = {
            "agents": [
                {
                    "name": "Agent名称",
                    "role": "角色定位",
                    "responsibilities": ["职责1", "职责2", "职责3"],
                    "skills": ["技能1", "技能2"],
                }
            ]
        }

        prompt = """ClawsJoy 系统有以下 Agent，请详细描述每个 Agent 的职责和能力：
- orchestrator (任务编排器)
- code_agent (代码助手)
- video_agent (视频制作助手)
- youtube_agent (YouTube助手)
- security_agent (安全助手)
- memory_manager (记忆管理助手)
- decision_agent (决策Agent)
- chat_agent (聊天Agent)
- personal_butler (私人管家)
- analysis_agent (数据分析师)

请为每个 Agent 生成详细的职责描述，每个 Agent 至少 3 个职责。"""

        return self.generate_with_schema(prompt, schema)

    def generate_architecture_desc(self) -> str:
        """生成架构描述（自由格式但约束长度）"""
        prompt = """请描述 ClawsJoy 的系统架构，包括以下层级：
1. 用户层
2. 安全层
3. Agent 协作层
4. 技能层
5. 记忆层
6. 基础设施层

要求：
- 每层用 2-3 句话描述
- 说明各层之间的交互关系
- 突出技术特点

输出纯文本，不要用 JSON。"""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 800},
                },
                timeout=config_helper.get_timeout("llm"),
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as e:
            pass
        return ""

    def generate_skill_desc(self, skill_name: str) -> str:
        """生成技能描述"""
        prompt = f"""请描述 ClawsJoy 的 {skill_name} 技能：
- 它有什么功能？
- 什么时候使用？
- 如何使用？

要求：3-5 句话，简洁明了。"""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 300},
                },
                timeout=unified_config.get("timeouts.default", 30),
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as e:
            pass
        return "SVG图表生成技能"


if __name__ == "__main__":
    gen = StructuredGenerator()

    print("=" * 60)
    print("生成 Agent 描述（结构化 JSON）")
    print("=" * 60)
    result = gen.generate_agent_description()
    if result.get("agents"):
        for agent in result["agents"][:3]:
            print(f"\n📌 {agent.get('name')}")
            print(f"   角色: {agent.get('role')}")
            print(f"   职责: {', '.join(agent.get('responsibilities', [])[:2])}")

    print("\n" + "=" * 60)
    print("生成架构描述（自由格式）")
    print("=" * 60)
    arch = gen.generate_architecture_desc()
    print(arch[:500])
