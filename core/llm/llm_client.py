#!/usr/bin/env python3
"""Llm Client - Llm Client 模块"""

import requests

from core.lib.config_helper import get_llm_endpoint, get_llm_model, get_timeout


class LLMClient:
    def __init__(self, model: str = None, url: str = None):
        self.model = model if model else get_llm_model(fast=True)
        self.url = url if url else f"{get_llm_endpoint()}/api/generate"

    def chat(self, prompt: str) -> str:
        try:
            response = requests.post(
                self.url,
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=get_timeout("llm"),
            )
            if response.status_code == 200:
                return response.json().get("response", "无响应内容")
        except Exception as e:
            print(f"LLM 调用错误: {e}")
        return "抱歉，我暂时无法回答这个问题。"


llm_client = LLMClient()
