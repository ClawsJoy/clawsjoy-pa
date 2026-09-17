#!/usr/bin/env python3
"""Llm Service - Llm Service 模块

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

"""
LLM 服务 - 支持 Ollama
"""
import json
from typing import Any, Dict

import requests


class LLMService:
    def __init__(self, base_url: str = get_llm_endpoint()):
        self.base_url = base_url
        self.default_model = unified_config.get("llm.default_model", get_llm_model())

    def generate(self, prompt: str, model: str = None) -> str:
        """生成回复"""
        model = model or self.default_model
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=get_timeout("llm"),
            )
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                return f"LLM 调用失败: {response.status_code}"
        except Exception as e:
            return f"LLM 调用失败: {str(e)}"

    def chat(self, messages: list, model: str = None) -> str:
        """对话模式"""
        model = model or self.default_model
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
                timeout=get_timeout("llm"),
            )
            if response.status_code == 200:
                return response.json().get("message", {}).get("content", "")
            else:
                return f"LLM 调用失败: {response.status_code}"
        except Exception as e:
            return f"LLM 调用失败: {str(e)}"


llm_service = LLMService()
