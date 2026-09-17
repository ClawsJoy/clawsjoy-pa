#!/usr/bin/env python3
"""Llm Client - Llm Client 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import get_llm_model

"""智能 LLM 客户端 - 支持多 provider"""
import json
from pathlib import Path
from typing import Dict, List, Optional

import requests
import yaml

from core.lib.unified_config import unified_config


class SmartLLMClient:
    """智能 LLM 客户端"""

    def __init__(self):
        self.config = self._load_config()
        self._init_provider()

    def _load_config(self) -> Dict:
        config_file = Path("config/butler/butler.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                return yaml.safe_load(f).get("llm", {})
        return {
            "provider": "ollama",
            "model": get_llm_model(fast=True),
            "temperature": 0.7,
            "timeout": 30,
        }

    def _init_provider(self):
        """初始化 provider"""
        self.provider = self.config.get("provider", "ollama")
        self.model = self.config.get("model", get_llm_model(fast=True))
        self.temperature = self.config.get("temperature", 0.7)
        self.timeout = self.config.get("timeout", 30)

        if self.provider == "ollama":
            self.api_url = (
                unified_config.get("llm.endpoint", "http://localhost:11434")
                + "/api/chat"
            )
        elif self.provider == "openai":
            self.api_url = "https://api.openai.com/v1/chat/completions"
        else:
            self.api_url = self.config.get("api_url", "")

    def chat(self, messages: List[Dict]) -> str:
        """发送聊天请求"""
        try:
            if self.provider == "ollama":
                return self._chat_ollama(messages)
            elif self.provider == "openai":
                return self._chat_openai(messages)
            else:
                return self._fallback(messages[-1].get("content", ""))
        except Exception as e:
            print(f"LLM 调用失败: {e}")
            return self._fallback(messages[-1].get("content", ""))

    def _chat_ollama(self, messages: List[Dict]) -> str:
        """Ollama API"""
        response = requests.post(
            self.api_url,
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": self.temperature},
            },
            timeout=self.timeout,
        )

        if response.status_code == 200:
            result = response.json()
            return result.get("message", {}).get("content", "")
        return ""

    def _chat_openai(self, messages: List[Dict]) -> str:
        """OpenAI API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.get('api_key', '')}",
        }
        response = requests.post(
            self.api_url,
            headers=headers,
            json={
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
            },
            timeout=self.timeout,
        )

        if response.status_code == 200:
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
        return ""

    def _fallback(self, user_input: str) -> str:
        """备用响应"""
        return f"您好，我是您的私人管家。收到您的消息：{user_input[:50]}"

    def is_available(self) -> bool:
        """检查 LLM 服务是否可用"""
        if self.provider == "ollama":
            try:
                resp = requests.get(
                    f"http://{unified_config.get('llm.endpoint', 'f"http://{{unified_config.get("services.gateway.host", "localhost")}}:11434"')}/api/tags",
                    timeout=5,
                )
                return resp.status_code == 200
            except Exception as e:
                return False
        return True


# 全局实例
llm_client = SmartLLMClient()

# 禁用代理
import os

os.environ["no_proxy"] = "localhost,127.0.0.1"
