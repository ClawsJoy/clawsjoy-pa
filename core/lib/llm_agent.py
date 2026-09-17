#!/usr/bin/env python3
"""Llm Agent - Llm Agent 模块

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
from core.lib.unified_config import unified_config

"""LLM Agent 核心 - 让 LLM 思考，系统执行"""

import json
import re

import requests

from core.lib.skill_loader_v3 import skill_loader
from core.lib.unified_config import unified_config


class LLMAgent:
    """LLM 作为大脑，系统作为手脚"""

    # 告诉 LLM 它有什么工具
    TOOLS = {
        "math": {"desc": "数学计算", "用法": {"expression": "算式，如 '10+20'"}},
        "manju_maker": {"desc": "制作漫剧视频", "用法": {"topic": "视频主题"}},
        "ai_image": {"desc": "生成图片", "用法": {"prompt": "图片描述"}},
        "tts": {"desc": "文字转语音", "用法": {"text": "要朗读的文字"}},
        "memory_query": {"desc": "查询记忆", "用法": {"query": "查询内容"}},
        "spider": {"desc": "采集图片", "用法": {"keyword": "搜索关键词"}},
        "add_subtitles": {"desc": "添加字幕", "用法": {"text": "字幕内容"}},
    }

    @classmethod
    def think_and_act(cls, user_request):
        """LLM 思考并输出行动计划"""

        # 第一步：让 LLM 理解并规划
        plan = cls._plan(user_request)
        if not plan:
            return {"success": False, "error": "无法规划"}

        # 第二步：系统执行计划
        results = []
        for action in plan.get("actions", []):
            result = cls._execute_action(action)
            results.append(result)

        return {
            "success": all(r.get("success") for r in results),
            "thought": plan.get("thought"),
            "plan": plan.get("actions"),
            "results": results,
        }

    @classmethod
    def _plan(cls, user_request):
        """LLM 规划"""

        tools_desc = "\n".join(
            [f"- {name}: {info['desc']}" for name, info in cls.TOOLS.items()]
        )

        prompt = f"""你是 ClawsJoy 的智能大脑。用户说: "{user_request}"

你有哪些工具:
{tools_desc}

请思考并输出 JSON 行动计划:
{{
  "thought": "你的思考过程（用户想要什么？需要哪些步骤？）",
  "actions": [
    {{"tool": "工具名", "params": {{"参数名": "参数值"}}}},
    {{"tool": "工具名", "params": {{}}}}
  ]
}}
只输出 JSON。"""

        try:
            resp = requests.post(
                f"{unified_config.LLM_ENDPOINT}/api/generate",
                json={
                    "model": unified_config.get_llm_config().get(
                        "default_model",
                        unified_config.get_llm_config().get(
                            "default_model",
                            unified_config.get("llm.default_model", get_llm_model()),
                        ),
                    ),
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=45,
            )
            content = resp.json().get("response", "{}")
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            print(f"规划失败: {e}")

        return None

    @classmethod
    def _execute_action(cls, action):
        """系统执行单个动作"""
        tool = action.get("tool")
        params = action.get("params", {})

        try:
            result = skill_loader.execute(tool, params)
            return {
                "tool": tool,
                "success": result.get("success", False),
                "result": result,
            }
        except Exception as e:
            return {"tool": tool, "success": False, "error": str(e)}


# 快捷调用
def do(what):
    return LLMAgent.think_and_act(what)
