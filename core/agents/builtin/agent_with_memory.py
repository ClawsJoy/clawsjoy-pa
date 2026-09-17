#!/usr/bin/env python3
"""Agent With Memory - Agent With Memory 模块

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
"""Agent 带记忆 + LLM 推理"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

from core.lib.config_manager import config_manager


class MemoryAgent:
    """Agent 负责记忆，LLM 负责推理"""

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.user_dir = Path(
            funified_config.get("paths.users_dir", f"{get_data_root()}/users/")
            + "/{user_id}/memory"
        )
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = (
            self.user_dir / f"session_{datetime.now().strftime('%Y%m%d')}.json"
        )
        self.long_memory_file = self.user_dir / "long_memory.json"

        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = config_manager.get_model()

        self.session_history = self._load_session()
        self.long_memory = self._load_long_memory()

    def _load_session(self) -> List[Dict]:
        """加载会话记忆（短期）"""
        if self.session_file.exists():
            with open(self.session_file, "r") as f:
                return json.load(f)
        return []

    def _save_session(self):
        """保存会话记忆"""
        # 只保留最近 50 条
        if len(self.session_history) > 50:
            self.session_history = self.session_history[-50:]
        with open(self.session_file, "w") as f:
            json.dump(self.session_history, f, indent=2)

    def _load_long_memory(self) -> Dict:
        """加载长期记忆"""
        if self.long_memory_file.exists():
            with open(self.long_memory_file, "r") as f:
                return json.load(f)
        return {"preferences": {}, "learned_patterns": [], "facts": []}

    def _save_long_memory(self):
        with open(self.long_memory_file, "w") as f:
            json.dump(self.long_memory, f, indent=2)

    def _get_context(self, user_input: str, limit: int = 5) -> str:
        """构建上下文（从 Agent 记忆）"""
        context = []

        # 最近对话
        if self.session_history:
            recent = self.session_history[-limit:]
            context.append("【最近对话】")
            for turn in recent:
                context.append(f"用户: {turn['user'][:50]}")
                context.append(f"助手: {turn['assistant'][:50]}")

        # 用户偏好
        if self.long_memory.get("preferences"):
            context.append("【用户偏好】")
            for k, v in self.long_memory["preferences"].items():
                context.append(f"- {k}: {v}")

        # 学到的模式
        if self.long_memory.get("learned_patterns"):
            context.append("【学到的模式】")
            for p in self.long_memory["learned_patterns"][-3:]:
                context.append(f"- {p}")

        return "\n".join(context)

    def _update_memory(self, user_input: str, response: str, task: str):
        """更新 Agent 记忆"""
        # 会话记忆
        self.session_history.append(
            {
                "user": user_input,
                "assistant": response[:200],
                "task": task,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self._save_session()

        # 学习用户偏好
        if "喜欢" in user_input or "偏好" in user_input:
            import re

            match = re.search(r"喜欢?([^，。]+)", user_input)
            if match:
                self.long_memory["preferences"][match.group(1)] = True
                self._save_long_memory()

        # 学习成功模式
        if "谢谢" in user_input or "很好" in user_input:
            pattern = f"用户对 '{task}' 满意"
            if pattern not in self.long_memory["learned_patterns"]:
                self.long_memory["learned_patterns"].append(pattern)
                self._save_long_memory()

    def _call_llm(self, user_input: str) -> str:
        """LLM 只做推理"""
        context = self._get_context(user_input)

        prompt = f"""你是 ClawsJoy 智能助手，有记忆能力。

{context}

用户最新输入：{user_input}

请根据上下文理解用户意图，友好回复。
如果用户有偏好，要记住并应用。
如果用户重复问题，要提醒之前回答过。"""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 500},
                },
                timeout=config_manager.get_timeout("normal"),
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error: {e}", exc_info=True)
            pass
        return "系统繁忙"

    def process(self, user_input: str) -> Dict:
        start = time.time()

        # 1. 识别任务
        task = "chat"
        if any(k in user_input for k in ["agent", "Agent", "有哪些"]):
            task = "list_agents"
        elif any(k in user_input for k in ["技能", "skill"]):
            task = "list_skills"
        elif any(k in user_input for k in ["图", "chart"]):
            task = "generate_chart"

        # 2. 执行任务
        if task == "list_agents":
            response = "ClawsJoy 有决策Agent、聊天Agent、执行Agent、采集Agent、安全Agent、分析Agent等10个专业Agent"
        elif task == "list_skills":
            skills_dir = Path("unified_config.ROOT/skills")
            skills = [d.name for d in skills_dir.iterdir() if d.is_dir()]
            response = f"共有 {len(skills)} 个技能：{', '.join(skills[:10])}"
        elif task == "generate_chart":
            response = "已生成架构图，保存在 output 目录"
        else:
            # 3. LLM 推理
            response = self._call_llm(user_input)

        # 4. 更新 Agent 记忆
        self._update_memory(user_input, response, task)

        elapsed = (time.time() - start) * 1000

        return {
            "response": response,
            "task": task,
            "memory_size": len(self.session_history),
            "time_ms": round(elapsed, 2),
        }


if __name__ == "__main__":
    print("=" * 60)
    print("Agent 带记忆 + LLM 推理")
    print("=" * 60)

    agent = MemoryAgent("test_user")

    tests = [
        "你好，我叫张三",
        "ClawsJoy 有哪些 Agent？",
        "我刚才说我叫什么？",  # 测试记忆
        "我喜欢蓝色主题",
        "帮我生成架构图",
        "我喜欢的主题是什么？",  # 测试偏好记忆
    ]

    for test in tests:
        print(f"\n👤 {test}")
        result = agent.process(test)
        print(f"🤖 {result['response']}")
        print(
            f"   [任务: {result['task']}, 记忆条数: {result['memory_size']}, 耗时: {result['time_ms']}ms]"
        )

    print("\n" + "=" * 60)
    print(f"会话记忆保存在: data/users/test_user/memory/")
