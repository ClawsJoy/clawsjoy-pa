#!/usr/bin/env python3
"""Teach Llm - Teach Llm 模块

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
from core.lib.constants import PROJECT_ROOT
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""教会 LLM 我的分析能力"""

import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, "PROJECT_ROOT")

from core.lib.architect_prompt import get_architect_prompt


class ArchitectTeacher:
    def __init__(self):
        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = unified_config.get_llm_config().get(
            "fast_model",
            unified_config.get_llm_config().get(
                "fast_model",
                unified_config.get("llm.fast_model", get_llm_model(fast=True)),
            ),
        )
        self.learned = []

    def teach(self, question: str, context: str = "") -> str:
        """用架构师框架教 LLM"""
        prompt = get_architect_prompt(question, context)

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 1000, "temperature": 0.3},
                },
                timeout=get_timeout("llm"),
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as e:
            print(f"教学失败: {e}")

        return ""

    def train_on_problems(self, problems: list):
        """用真实问题训练"""
        for problem in problems:
            print(f"\n📚 教学问题: {problem}")
            answer = self.teach(problem)
            print(f"📖 学到: {answer[:200]}...")
            self.learned.append({"question": problem, "answer": answer})
        return self.learned


if __name__ == "__main__":
    teacher = ArchitectTeacher()

    problems = [
        "ClawsJoy 系统如何实现用户数据隔离？",
        "Agent 之间如何通信？",
        "如何让 LLM 输出稳定的 JSON 格式？",
        "系统响应慢，如何排查？",
    ]

    print("=" * 60)
    print("教会 LLM 架构师的分析能力")
    print("=" * 60)

    teacher.train_on_problems(problems)

    print("\n" + "=" * 60)
    print("现在 LLM 学会了架构师的分析框架")
