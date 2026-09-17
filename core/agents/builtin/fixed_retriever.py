#!/usr/bin/env python3
"""Fixed Retriever - Fixed Retriever 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""修复版检索 Agent"""

import re
import sys
from typing import Dict, Tuple

import requests

from core.lib.cross_session_memory import CrossSessionMemory
from core.lib.memory_vector import vector_memory


class FixedRetriever:
    VERSION = "6.2.0"

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.memory = CrossSessionMemory(user_id)
        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = model_config.get_fast_model()

    def _extract_search_term(self, user_input: str) -> str:
        """提取搜索词 - 保留完整关键词"""
        # 移除搜索动作词，保留完整名词
        search_actions = [
            "找一下",
            "搜索",
            "查找",
            "查一下",
            "帮我找",
            "找",
            "查",
            "有没有",
            "在哪里",
            "在哪",
        ]

        term = user_input
        for action in search_actions:
            term = term.replace(action, "")

        # 保留完整的名词短语
        term = term.strip().strip("，。？！")

        # 如果提取结果太短，使用原文
        if len(term) < 2:
            term = user_input

        return term

    def _classify(self, user_input: str) -> Tuple[str, str]:
        lower = user_input.lower()

        # 搜索任务
        search_keywords = ["找", "搜索", "查找", "资料", "文档", "总结", "报告"]
        if any(kw in user_input for kw in search_keywords):
            query = self._extract_search_term(user_input)
            return "search", query

        if any(g in user_input for g in ["你好", "hi"]):
            return "greeting", ""

        if re.match(r"^[我][叫][\s]*", user_input):
            return "self_intro", user_input

        if "你是谁" in user_input:
            return "ask_who", ""

        return "chat", user_input

    def _search(self, query: str) -> str:
        """搜索向量库"""
        print(f"   🔍 搜索词: '{query}'")

        # 多种搜索策略
        results = vector_memory.search(query, n=5)

        # 如果没找到，尝试拆分关键词
        if not results or len(results) == 0:
            keywords = re.findall(r"[\u4e00-\u9fa5]{2,}", query)
            for kw in keywords[:3]:
                kw_results = vector_memory.search(kw, n=3)
                results.extend(kw_results)

        # 过滤有效结果
        valid = []
        for r in results:
            text = r.get("text", "")
            if text and len(text) > 100:
                valid.append(text[:800])

        if valid:
            return "\n\n---\n\n".join(valid[:2])

        return ""

    def process(self, user_input: str) -> Dict:
        task_type, task_param = self._classify(user_input)
        print(f"   🎯 任务: {task_type} -> '{task_param[:40]}'")

        name = self.memory.recall().get("name")

        if task_type == "search":
            results = self._search(task_param)
            if results:
                response = f"找到相关资料：\n\n{results}"
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
    agent = FixedRetriever("John")

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
