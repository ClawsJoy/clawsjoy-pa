#!/usr/bin/env python3
"""Llm Retriever - Llm Retriever 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""LLM 辅助检索 Agent - 绕过向量库匹配问题"""

import json
import re
import sys
from pathlib import Path

import requests

from core.lib.cross_session_memory import CrossSessionMemory


class LLMRetriever:
    VERSION = "6.3.0"

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.memory = CrossSessionMemory(user_id)
        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = model_config.get_fast_model()

        # 加载内置知识库
        self.knowledge_base = self._load_knowledge()

    def _load_knowledge(self) -> dict:
        """加载内置知识库"""
        knowledge = {}

        # 读取架构师总结
        arch_file = Path("docs/founder/ARCHITECT_SUMMARY.md")
        if arch_file.exists():
            knowledge["架构师总结"] = arch_file.read_text(encoding="utf-8")

        # 读取创始人资料
        founder_file = Path("docs/founder/CLAWSJOY_ORIGIN.md")
        if founder_file.exists():
            knowledge["创始人资料"] = founder_file.read_text(encoding="utf-8")

        # 读取 README
        readme_file = Path("README.md")
        if readme_file.exists():
            knowledge["项目介绍"] = readme_file.read_text(encoding="utf-8")

        return knowledge

    def _classify(self, user_input: str) -> tuple:
        lower = user_input.lower()

        if any(
            kw in user_input
            for kw in ["找", "搜索", "查", "资料", "文档", "总结", "报告"]
        ):
            # 提取关键词
            query = user_input
            for kw in ["找一下", "搜索", "查找", "查一下", "帮我找", "找", "查"]:
                query = query.replace(kw, "")
            query = query.strip().strip("，。？！")
            return "search", query

        if any(g in user_input for g in ["你好", "hi"]):
            return "greeting", ""

        if re.match(r"^[我][叫][\s]*", user_input):
            return "self_intro", user_input

        if "你是谁" in user_input:
            return "ask_who", ""

        return "chat", user_input

    def _search_knowledge(self, query: str) -> str:
        """在知识库中搜索"""
        results = []

        # 关键词匹配
        for title, content in self.knowledge_base.items():
            if any(kw in title for kw in ["架构师", "创始人", "总结", "资料"]):
                if any(
                    kw in query for kw in ["架构师", "创始人", "总结", "资料", "John"]
                ):
                    results.append(f"【{title}】\n{content[:800]}")

        if results:
            return "\n\n---\n\n".join(results)

        return ""

    def process(self, user_input: str) -> dict:
        task_type, task_param = self._classify(user_input)
        print(f"   🎯 任务: {task_type} -> '{task_param[:40]}'")

        name = self.memory.recall().get("name")

        if task_type == "search":
            # 先在知识库中搜索
            knowledge = self._search_knowledge(task_param)
            if knowledge:
                response = f"找到相关资料：\n\n{knowledge}"
            else:
                response = f"没有找到关于「{task_param}」的资料。可以试试「架构师总结」或「创始人资料」"

        elif task_type == "greeting":
            response = f"你好{f'，{name}' if name else ''}！我是 ClawsJoy"

        elif task_type == "self_intro":
            match = re.search(r"叫[\s]*([^\s，。]{2,4})", user_input)
            if match:
                self.memory.remember("name", match.group(1))
                response = f"你好，{match.group(1)}！我是 ClawsJoy"
            else:
                response = "你好！请告诉我你的名字"

        elif task_type == "ask_who":
            response = "我是 ClawsJoy，你的智能助手！"

        else:
            response = f"我是 ClawsJoy。收到：{user_input[:50]}"

        self.memory.record_interaction(user_input, response, task_type)
        return {"response": response}


if __name__ == "__main__":
    agent = LLMRetriever("John")

    tests = [
        "你好",
        "我叫 John",
        "你是谁",
        "找一下架构师的总结",
        "创始人的资料",
    ]

    for t in tests:
        print(f"\n👤 {t}")
        result = agent.process(t)
        print(f"🤖 {result['response']}")
        print("-" * 50)
