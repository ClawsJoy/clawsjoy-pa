#!/usr/bin/env python3
"""Llm Enhancer - Llm Enhancer 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import requests

from core.lib.unified_config import unified_config


class LLMEnhancer:
    """LLM 增强器"""

    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.model = unified_config.get("llm.fast_model", "qwen2.5:7b-instruct-q4_0-gpu")
        self.enabled = True

    def enhance_response(self, agent_name: str, user_input: str) -> str:
        if not self.enabled:
            return None

        llm_agents = ["chat_agent", "personal_butler", "butler"]
        if agent_name not in llm_agents:
            return None

        try:
            prompt = f"你是 {agent_name}，一个智能助手。请友好、专业地回答用户问题。\n\n用户: {user_input}\n\n助手:"
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=unified_config.get("timeouts.default", 30),
            )
            if response.status_code == 200:
                return response.json().get("response", "")
        except Exception as e:
            print(f"LLM 增强失败: {e}")
        return None

    def get_enhanced_capabilities(self):
        return {
            "llm_enabled": self.enabled,
            "model": self.model,
            "supported_agents": ["chat_agent", "personal_butler", "butler"],
            "features": ["智能对话", "上下文理解", "自然语言生成"],
        }


llm_enhancer = LLMEnhancer()
