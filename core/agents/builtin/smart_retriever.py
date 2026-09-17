#!/usr/bin/env python3
"""Smart Retriever - Smart Retriever 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import logging

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""智能检索 Agent - 自主理解用户意图"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

import requests

from core.lib.cross_session_memory import CrossSessionMemory
from core.lib.memory_vector import vector_memory


class SmartRetriever:
    VERSION = "5.5.0"

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.memory = CrossSessionMemory(user_id)
        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = model_config.get_fast_model()
        self.interaction_count = 0

    def _understand_intent(self, user_input: str) -> Dict:
        """让 LLM 理解用户意图"""
        prompt = f"""分析用户意图，返回 JSON。

用户："{user_input}"

可能意图：
- search: 搜索/查找/找资料
- greet: 问候/打招呼
- self_intro: 自我介绍/我叫xxx
- ask_who: 问你是谁/你叫什么
- chat: 其他

返回格式：{{"intent": "意图", "query": "搜索关键词（如果是search）"}}"""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 100},
                },
                timeout=15,
            )
            if resp.status_code == 200:
                response = resp.json().get("response", "")
                import re

                match = re.search(r"\{[^{}]*\}", response)
                if match:
                    return json.loads(match.group())
        except Exception as e:
            print(f"意图理解失败: {e}")

        return {"intent": "chat"}

    def _search_vector(self, query: str) -> str:
        """搜索向量库"""
        try:
            results = vector_memory.search(query, n=5)
            if results:
                texts = []
                for r in results:
                    text = r.get("text", "")[:500]
                    if text:
                        texts.append(
                            f"【来源: {r.get('metadata', {}).get('source', 'unknown')}】\n{text}"
                        )
                return "\n\n".join(texts)
        except Exception as e:
            print(f"搜索失败: {e}")
        return ""

    def _answer_with_context(self, user_input: str, context: str) -> str:
        """基于上下文回答"""
        name = self.memory.recall().get("name", "")

        prompt = f"""你是 ClawsJoy 智能助手。

{f'用户叫{name}。' if name else ''}
用户问："{user_input}"

{f'找到的相关资料：\n{context[:1500]}' if context else '没有找到相关资料。'}

请根据找到的资料回答用户。如果没有找到，告知用户没找到并建议换个关键词。
回复要简洁有用。"""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 500},
                },
                timeout=unified_config.get("timeouts.default", 30),
            )
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
        except Exception as e:
            print(f"回答生成失败: {e}")

        return "让我想想..."

    def process(self, user_input: str) -> Dict:
        self.interaction_count += 1
        lower = user_input.lower()
        name = self.memory.recall().get("name")

        # 规则快速响应（不调用 LLM 理解）
        if any(g in lower for g in ["你好", "hi"]):
            response = f"你好{f'，{name}' if name else ''}！我是 ClawsJoy"
        elif "你是谁" in lower:
            response = "我是 ClawsJoy，你的智能助手！"
        elif re.match(r"^[我][叫][\s]*([^\s，。]{2,4})$", user_input.strip()):
            match = re.search(r"叫[\s]*([^\s，。]{2,4})", user_input)
            if match:
                self.memory.remember("name", match.group(1))
                name = match.group(1)
            response = f"你好，{name}！我是 ClawsJoy"
        else:
            # 复杂任务：LLM 理解意图
            intent = self._understand_intent(user_input)

            if intent.get("intent") == "search":
                query = intent.get("query", user_input)
                print(f"   🔍 搜索: {query}")
                context = self._search_vector(query)
                response = self._answer_with_context(user_input, context)
            else:
                response = self._answer_with_context(user_input, "")

        self.memory.record_interaction(user_input, response, "chat")

        if self.interaction_count % 10 == 0:
            print(f"   💭 梦境循环 #{self.interaction_count // 10}")

        return {"response": response, "task": "chat"}


if __name__ == "__main__":
    agent = SmartRetriever("John")

    # 测试各种查询
    tests = [
        "你好",
        "我叫 John",
        "找一下架构师的总结",
        "创始人的资料",
        "关于 ClawsJoy 的起源",
        "John 是谁",
    ]

    for t in tests:
        print(f"\n👤 {t}")
        result = agent.process(t)
        print(f"🤖 {result['response']}")
        print("-" * 40)
