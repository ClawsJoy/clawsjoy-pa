#!/usr/bin/env python3
"""Life Cycle Config Driven - Life Cycle Config Driven 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""配置驱动的生命闭环 Agent v5.3 - 修复版"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests
import yaml

from core.lib.cross_session_memory import CrossSessionMemory
from core.lib.metacognition import Metacognition
from core.lib.unified_config import unified_config


class LifeCycleConfigDriven:
    """配置驱动的生命闭环 Agent"""

    VERSION = "5.3.0"

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.config = self._load_config()
        self.memory = CrossSessionMemory(user_id)
        self.metacognition = Metacognition(f"agent_{user_id}")

        self.dreaming_data = {"short_term": [], "long_term": [], "cycles": 0}

        self.ollama_url = "config_loader.get_ollama_url()"
        self.model = model_config.get_fast_model()

        self.reflection_interval = self.config["reflection"]["interval"]
        self.dreaming_interval = self.config["dreaming"]["interval"]
        self.short_term_max = self.config["dreaming"]["short_term_max"]
        self.long_term_max = self.config["dreaming"]["long_term_max"]
        self.quality_excellent = self.config["reflection"]["quality_thresholds"][
            "excellent"
        ]
        self.quality_good = self.config["reflection"]["quality_thresholds"]["good"]

        user_info = self.memory.recall()
        print(f"🧠 配置驱动生命闭环 v{self.VERSION}")
        print(f"📝 用户: {user_info.get('name', '新用户')}")

    def _load_config(self) -> Dict:
        config_file = Path("config/driver/life_cycle.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                return unified_config.get("agent_lifecycle", {})
        return {
            "reflection": {
                "interval": 5,
                "quality_thresholds": {"excellent": 0.8, "good": 0.5},
            },
            "dreaming": {"interval": 10, "short_term_max": 20, "long_term_max": 100},
            "perception": {"excluded_words": ["什么", "谁", "怎么"]},
        }

    def _perceive(self, text: str) -> Dict:
        excluded = self.config["perception"]["excluded_words"]

        # 名字提取
        name_match = re.search(r"^[我][叫][\s]*([^\s，。]{2,4})$", text.strip())
        if name_match:
            name = name_match.group(1)
            if name not in excluded:
                self.memory.remember("name", name)
                return {"type": "self_intro", "value": name}

        # 偏好提取
        pref_match = re.search(r"喜欢[\s]*([^，。]{2,8})$", text)
        if pref_match:
            pref = pref_match.group(1)
            if pref not in excluded:
                self.memory.remember("preference", pref)
                return {"type": "preference", "value": pref}

        lower = text.lower()
        if any(g in lower for g in ["你好", "hi"]):
            return {"type": "greeting"}
        if any(q in lower for q in ["我叫什么", "我名字", "还记得我吗"]):
            return {"type": "ask_name"}
        if any(q in lower for q in ["喜欢什么", "偏好"]):
            return {"type": "ask_preference"}
        if "agent" in lower and ("有哪些" in lower or "列表" in lower):
            return {"type": "list_agents"}

        return {"type": "chat", "text": text}

    def _act(self, perception: Dict) -> Tuple[str, str]:
        ptype = perception.get("type")
        user_info = self.memory.recall()
        name = user_info.get("name")
        prefs = user_info.get("preferences", [])

        # 定义系统身份
        if ptype == "greeting":
            return (
                f"你好{f'，{name}' if name else ''}！我是 ClawsJoy 智能助手，有什么可以帮你的？",
                "greeting",
            )
        elif ptype == "self_intro":
            return (
                f"你好，{perception.get('value')}！我是 ClawsJoy，很高兴认识你",
                "self_intro",
            )
        elif ptype == "preference":
            return (f"好的，我记住了（我是 ClawsJoy）", "preference")
        elif ptype == "ask_name":
            return (
                (
                    f"当然记得！你是{name}呀"
                    if name
                    else "我是 ClawsJoy，你还没告诉我名字呢"
                ),
                "query_name",
            )
        elif ptype == "ask_preference":
            return (
                (
                    f"你喜欢{', '.join(prefs)}"
                    if prefs
                    else "我是 ClawsJoy，你还没告诉我你的偏好呢"
                ),
                "query_pref",
            )
        elif ptype == "list_agents":
            return (
                "我是 ClawsJoy 智能助手。系统有决策Agent、聊天Agent、执行Agent、采集Agent、安全Agent、分析Agent",
                "list_agents",
            )
        else:
            # 简单回应，不调用 LLM
            return (f"我是 ClawsJoy。收到：{perception.get('text', '')[:50]}", "chat")

    def _record(self, user_input: str, response: str):
        self.memory.record_interaction(user_input, response, "")
        self.dreaming_data["short_term"].append(
            {
                "user": user_input[:100],
                "response": response[:100],
                "time": datetime.now().isoformat(),
            }
        )

        if len(self.dreaming_data["short_term"]) > self.short_term_max:
            self.dreaming_data["short_term"] = self.dreaming_data["short_term"][
                -self.short_term_max :
            ]

    def process(self, user_input: str) -> Dict:
        start = time.time()
        perception = self._perceive(user_input)
        response, task = self._act(perception)
        self._record(user_input, response)

        total = self.memory.recall().get("total_interactions", 0)

        if total % self.reflection_interval == 0 and total > 0:
            print(f"   💭 反思: 已处理 {total} 次交互")

        if total % self.dreaming_interval == 0 and total > 0:
            self.dreaming_data["cycles"] += 1
            print(f"   💭 梦境循环 #{self.dreaming_data['cycles']}")

        elapsed = (time.time() - start) * 1000

        return {
            "response": response,
            "task": task,
            "time_ms": round(elapsed, 2),
            "perception": perception["type"],
        }


if __name__ == "__main__":
    agent = LifeCycleConfigDriven("test")
    print(agent.process("你好"))
