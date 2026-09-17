#!/usr/bin/env python3
"""Architect Agent - Architect Agent 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import logging

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""架构师 Agent - 具备我（架构师）的分析能力"""

import json
import sys
import time
from pathlib import Path

import requests

from core.lib.architect_prompt import get_architect_prompt
from core.lib.config_manager import config_manager


class ArchitectAgent:
    def __init__(self):
        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = config_manager.get_model()

    def think(self, question: str, context: str = "") -> str:
        """像架构师一样思考"""
        prompt = get_architect_prompt(question, context)

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 800},
                },
                timeout=config_manager.get_timeout("long"),
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as e:
            return f"思考失败: {e}"

        return "无法分析"

    def answer(self, question: str) -> dict:
        start = time.time()
        response = self.think(question)
        elapsed = (time.time() - start) * 1000

        return {"question": question, "answer": response, "time_ms": round(elapsed, 2)}


agent = ArchitectAgent()


if __name__ == "__main__":
    print("=" * 60)
    print("架构师 Agent - 具备分析能力")
    print("=" * 60)

    questions = [
        "如何让 LLM 输出更稳定？",
        "ClawsJoy 系统有哪些安全问题需要注意？",
        "如何优化 Agent 之间的通信效率？",
    ]

    for q in questions:
        print(f"\n📋 问题: {q}")
        result = agent.answer(q)
        print(f"🎯 回答:\n{result['answer'][:400]}")
        print(f"\n   [耗时: {result['time_ms']}ms]")
        print("-" * 40)
