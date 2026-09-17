#!/usr/bin/env python3
"""Pure Vector Agent - Pure Vector Agent 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""纯向量检索 Agent - 无硬编码关键词"""

import re
import sys
from typing import Dict, Tuple

from core.lib.cross_session_memory import CrossSessionMemory
from core.lib.memory_vector import vector_memory


class PureVectorAgent:
    VERSION = "6.7.0"

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.memory = CrossSessionMemory(user_id)

    def _classify(self, user_input: str) -> Tuple[str, str]:
        """识别任务 - 无硬编码关键词"""
        lower = user_input.lower()

        # 搜索意图（通过语义，不是关键词）
        # 让 LLM 判断？暂时用简单规则
        search_hints = ["找", "查", "搜"]
        if any(h in user_input for h in search_hints):
            # 提取搜索词（去掉动作词）
            query = user_input
            for h in search_hints:
                query = query.replace(h, "")
            query = query.strip().strip("，。？！")
            return "search", query if query else user_input

        if "你好" in user_input or "hi" in lower:
            return "greeting", ""

        if re.match(r"^[我][叫]", user_input):
            return "self_intro", user_input

        if "你是谁" in user_input:
            return "ask_who", ""

        return "chat", user_input

    def _search(self, query: str, min_score: float = 0.4) -> str:
        """纯向量检索 - 只依赖 ChromaDB"""
        print(f"   🔍 检索: '{query}'")

        results = vector_memory.search(query, n=10)

        # 按相似度过滤，取最高分的内容
        best = None
        best_score = 0

        for r in results:
            text = r.get("text", "")
            score = r.get("similarity", 0)

            # 只取有实质内容且相似度较高的
            if len(text) > 200 and score > min_score and score > best_score:
                best = text[:1500]
                best_score = score

        if best:
            print(f"   📊 最高相似度: {best_score:.2f}")
            return best

        return ""

    def process(self, user_input: str) -> Dict:
        task_type, task_param = self._classify(user_input)
        print(f"   🎯 任务: {task_type} -> '{task_param[:40]}'")

        name = self.memory.recall().get("name")

        if task_type == "search":
            result = self._search(task_param)
            if result:
                response = f"找到相关资料：\n\n{result}"
            else:
                response = f"没有找到关于「{task_param}」的资料。"

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
            response = f"我是 ClawsJoy。{user_input[:50]}"

        self.memory.record_interaction(user_input, response, task_type)
        return {"response": response}


if __name__ == "__main__":
    agent = PureVectorAgent("John")

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
        print(f"🤖 {result['response'][:400]}")
        print("-" * 50)
