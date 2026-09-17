#!/usr/bin/env python3
"""Enhanced Retriever - Enhanced Retriever 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import logging

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""增强检索 Agent - 优先中文内容"""

import json
import re
import sys
from typing import Dict, Tuple

import requests

from core.lib.cross_session_memory import CrossSessionMemory
from core.lib.memory_vector import vector_memory


class EnhancedRetriever:
    VERSION = "6.1.0"

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.memory = CrossSessionMemory(user_id)
        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = model_config.get_fast_model()

    def _classify_task(self, user_input: str) -> Tuple[str, str]:
        """识别任务类型"""
        lower = user_input.lower()

        search_keywords = [
            "找",
            "搜索",
            "查找",
            "查",
            "资料",
            "文档",
            "总结",
            "报告",
            "介绍",
        ]
        if any(kw in user_input for kw in search_keywords):
            query = user_input
            for kw in search_keywords:
                query = query.replace(kw, "")
            query = query.strip().strip("，。？！")
            return "search", query if query else user_input

        if any(g in user_input for g in ["你好", "hi"]):
            return "greeting", ""

        if re.match(r"^[我][叫][\s]*", user_input):
            return "self_intro", user_input

        if "你是谁" in user_input:
            return "ask_who", ""

        return "chat", user_input

    def _search(self, query: str) -> str:
        """搜索 - 优先匹配中文"""
        if not query:
            return ""

        # 直接搜索原词
        results = vector_memory.search(query, n=5)

        # 过滤：优先返回包含中文的结果
        chinese_results = []
        for r in results:
            text = r.get("text", "")
            # 统计中文字符比例
            chinese_count = len(re.findall(r"[\u4e00-\u9fff]", text))
            if chinese_count > 50:  # 至少50个中文字符
                chinese_results.append(r)

        if chinese_results:
            return "\n\n---\n\n".join(
                [r.get("text", "")[:800] for r in chinese_results[:2]]
            )

        return ""

    def _execute_search(self, query: str) -> str:
        print(f"   🔍 搜索: '{query}'")
        results = self._search(query)

        if results:
            return f"找到相关资料：\n\n{results}"
        else:
            return f"没有找到关于「{query}」的资料。"

    def _execute_greeting(self) -> str:
        name = self.memory.recall().get("name")
        return f"你好{f'，{name}' if name else ''}！我是 ClawsJoy"

    def _execute_self_intro(self, user_input: str) -> str:
        match = re.search(r"叫[\s]*([^\s，。]{2,4})", user_input)
        if match:
            name = match.group(1)
            self.memory.remember("name", name)
            return f"你好，{name}！我是 ClawsJoy"
        return "你好！请告诉我你的名字"

    def _execute_ask_who(self) -> str:
        return "我是 ClawsJoy，你的智能助手！"

    def _execute_chat(self, user_input: str) -> str:
        name = self.memory.recall().get("name", "")
        prompt = f"""你是 ClawsJoy。{f'用户叫{name}。' if name else ''}
用户说："{user_input}"
请友好回复。"""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 150},
                },
                timeout=20,
            )
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error: {e}", exc_info=True)
            pass
        return f"收到：{user_input[:50]}"

    def process(self, user_input: str) -> Dict:
        task_type, task_param = self._classify_task(user_input)
        print(f"   🎯 任务: {task_type} -> '{task_param[:30]}'")

        if task_type == "search":
            response = self._execute_search(task_param)
        elif task_type == "greeting":
            response = self._execute_greeting()
        elif task_type == "self_intro":
            response = self._execute_self_intro(user_input)
        elif task_type == "ask_who":
            response = self._execute_ask_who()
        else:
            response = self._execute_chat(user_input)

        self.memory.record_interaction(user_input, response, task_type)
        return {"response": response, "task": task_type}


if __name__ == "__main__":
    agent = EnhancedRetriever("John")

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
