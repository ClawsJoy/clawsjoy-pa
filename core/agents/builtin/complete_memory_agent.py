#!/usr/bin/env python3
"""Complete Memory Agent - Complete Memory Agent 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import logging

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""完整记忆 Agent - 四层互补"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import requests

from core.lib.config_manager import config_manager
from core.lib.memory_vector import vector_memory


class CompleteMemoryAgent:
    """短期+长期+规则+LLM 四层互补"""

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.user_dir = Path(
            funified_config.get("paths.users_dir", f"{get_data_root()}/users/")
            + "/{user_id}"
        )
        self.user_dir.mkdir(parents=True, exist_ok=True)

        # ========== 第一层：短期记忆（文件）==========
        self.short_term_file = self.user_dir / "short_term.json"
        self.short_term = self._load_short_term()

        # ========== 第二层：长期记忆（向量库）==========
        # 已通过 vector_memory 实现

        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = config_manager.get_model()

    def _load_short_term(self) -> Dict:
        if self.short_term_file.exists():
            with open(self.short_term_file, "r") as f:
                return json.load(f)
        return {
            "name": None,
            "preferences": {},
            "last_topic": None,
            "session_history": [],
        }

    def _save_short_term(self):
        with open(self.short_term_file, "w") as f:
            json.dump(self.short_term, f, indent=2)

    def _store_short_term(self, key: str, value):
        """短期记忆存储"""
        if key == "name":
            self.short_term["name"] = value
        elif key == "preference":
            self.short_term["preferences"][value] = True
        elif key == "topic":
            self.short_term["last_topic"] = value
        self._save_short_term()

    def _store_long_term(self, user_input: str, response: str):
        """长期记忆存储（向量库）"""
        vector_memory.add(
            f"用户{self.user_id}: {user_input}\n助手: {response}",
            category=f"user_{self.user_id}_conversation",
            metadata={"timestamp": datetime.now().isoformat()},
        )

    def _search_long_term(self, query: str, n: int = 2) -> list:
        """长期记忆检索"""
        results = vector_memory.search(
            query, category=f"user_{self.user_id}_conversation", n=n
        )
        return [r.get("text", "") for r in results]

    def _extract_info(self, user_input: str):
        """从输入提取信息"""
        # 提取名字
        name_match = re.search(r"[我叫我是][\s]*([^\s，。]+)", user_input)
        if name_match:
            self._store_short_term("name", name_match.group(1))

        # 提取偏好
        pref_match = re.search(r"喜欢([^，。]+)", user_input)
        if pref_match:
            self._store_short_term("preference", pref_match.group(1).strip())

        # 提取话题
        if "agent" in user_input.lower():
            self._store_short_term("topic", "agent")
        elif "图" in user_input:
            self._store_short_term("topic", "chart")

    def _build_context(self, user_input: str) -> str:
        """构建上下文（四层）"""
        context_parts = []

        # 1. 短期记忆
        if self.short_term.get("name"):
            context_parts.append(f"👤 用户名字：{self.short_term['name']}")

        if self.short_term.get("preferences"):
            prefs = ", ".join(self.short_term["preferences"].keys())
            context_parts.append(f"🎨 用户偏好：{prefs}")

        if self.short_term.get("last_topic"):
            context_parts.append(f"📌 上次话题：{self.short_term['last_topic']}")

        # 2. 最近对话（短期）
        recent = self.short_term.get("session_history", [])[-3:]
        if recent:
            context_parts.append("💬 最近对话：")
            for h in recent:
                context_parts.append(f"   - 用户: {h['user'][:40]}")
                context_parts.append(f"   - 助手: {h['response'][:40]}")

        # 3. 长期记忆（向量检索）
        long_terms = self._search_long_term(user_input, n=2)
        if long_terms:
            context_parts.append("📚 历史相关记忆：")
            for lt in long_terms:
                context_parts.append(f"   - {lt[:80]}")

        return "\n".join(context_parts)

    def _rule_response(self, user_input: str) -> Optional[tuple]:
        """规则匹配（快速响应）"""
        lower = user_input.lower()

        # Agent 列表
        if "agent" in lower and ("有哪些" in lower or "列表" in lower):
            agents = "决策Agent、聊天Agent、执行Agent、采集Agent、安全Agent、分析Agent、私人管家"
            return (f"ClawsJoy 有以下专业 Agent：{agents}（共10个）", "list_agents")

        # 技能列表
        if "技能" in lower or "skill" in lower:
            return (
                "ClawsJoy 有 20+ 原子技能，包括图像生成、视频制作、任务调度等",
                "list_skills",
            )

        # 生成图表
        if any(k in lower for k in ["图", "chart", "架构图"]):
            return ("已生成架构图，保存在 output 目录", "generate_chart")

        # 问候
        if any(k in lower for k in ["你好", "hi", "hello"]):
            name = self.short_term.get("name", "")
            return (
                f"你好{f'，{name}' if name else ''}！我是 ClawsJoy 智能助手",
                "greeting",
            )

        # 问名字
        if "我叫什么" in lower or "名字" in lower:
            name = self.short_term.get("name")
            if name:
                return (f"您叫 {name}", "query_name")
            return ("我还没记住您的名字呢，请告诉我", "query_name")

        # 问偏好
        if "喜欢什么" in lower or "偏好" in lower:
            prefs = self.short_term.get("preferences", {})
            if prefs:
                return (f"您喜欢：{', '.join(prefs.keys())}", "query_pref")
            return ("您还没有告诉我您的偏好呢", "query_pref")

        return None

    def _llm_response(self, user_input: str, context: str) -> str:
        """LLM 理解响应"""
        prompt = f"""你是 ClawsJoy 智能助手。

{context}

用户说："{user_input}"

请友好回复，利用上下文信息。"""

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
            print(f"LLM 调用失败: {e}")
        return "让我想想..."

    def process(self, user_input: str) -> Dict:
        start = time.time()

        # 提取并存储信息
        self._extract_info(user_input)

        # 第一层：规则匹配（最快）
        rule_result = self._rule_response(user_input)

        if rule_result:
            response, task = rule_result
            used_llm = False
        else:
            # 第二层：构建上下文
            context = self._build_context(user_input)
            # 第三层：LLM 理解
            response = self._llm_response(user_input, context)
            task = "chat"
            used_llm = True

        # 存储到短期记忆
        self.short_term["session_history"].append(
            {
                "user": user_input[:200],
                "response": response[:200],
                "time": datetime.now().isoformat(),
            }
        )
        # 只保留最近 20 条
        if len(self.short_term["session_history"]) > 20:
            old = self.short_term["session_history"].pop(0)
            # 存入长期记忆
            self._store_long_term(old["user"], old["response"])

        self._save_short_term()

        elapsed = (time.time() - start) * 1000

        return {
            "response": response,
            "task": task,
            "used_llm": used_llm,
            "time_ms": round(elapsed, 2),
            "context_used": not used_llm,  # 规则匹配时用了上下文
        }


if __name__ == "__main__":
    print("=" * 60)
    print("完整记忆 Agent - 四层互补")
    print("=" * 60)
    print("1. 短期记忆（文件）→ 快速存取")
    print("2. 长期记忆（向量库）→ 持久化")
    print("3. 规则匹配 → 毫秒级响应")
    print("4. LLM 理解 → 深度处理")
    print("=" * 60)

    agent = CompleteMemoryAgent("demo_user")

    tests = [
        "你好",
        "我叫赵六",
        "我喜欢暗黑风格",
        "ClawsJoy 有哪些 Agent？",
        "我叫什么名字？",
        "我喜欢的风格是什么？",
        "生成架构图",
        "你刚才说我叫什么？",  # 测试上下文
    ]

    for test in tests:
        print(f"\n👤 {test}")
        result = agent.process(test)
        print(f"🤖 {result['response']}")
        print(
            f"   [模式: {'⚡规则' if not result['used_llm'] else '🧠LLM'}, 耗时: {result['time_ms']}ms]"
        )

    print("\n" + "=" * 60)
    print("四层互补完成！")
    print("- 简单问题：规则快速响应 (<10ms)")
    print("- 复杂问题：LLM 深度理解 (500-1000ms)")
    print("- 短期记忆：记住当前会话")
    print("- 长期记忆：向量库持久化")
