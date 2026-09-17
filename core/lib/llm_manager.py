#!/usr/bin/env python3
"""Llm Manager - Llm Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config

"""LLM 管理器"""
import requests

from core.lib.config import config


class LLMManager:
    def __init__(self):
        # 创建 Session 复用连接
        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.5)
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.endpoint = unified_config.get("llm", {}).get(
            "endpoint", "http://localhost:11434"
        )
        self.default_model = unified_config.get("llm", {}).get(
            "default_model",
            unified_config.get("llm", {}).get(
                "default_model",
                unified_config.get("llm", {}).get(
                    "default_model",
                    unified_config.get("llm.default_model", get_llm_model()),
                ),
            ),
        )
        self.providers = {"ollama": {"endpoint": self.endpoint}}

    def generate(
        self,
        prompt,
        model=None,
        provider=None,
        system=None,
        temperature=0.7,
        max_tokens=2000,
        timeout=60,
    ):
        """生成回复，支持 system prompt"""
        model = model or self.default_model
        try:
            if system:
                # 使用 chat 端点
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                }
                resp = self.session.post(
                    f"{self.endpoint}/api/chat", json=payload, timeout=timeout
                )
                data = resp.json()
                return data.get("message", {}).get("content", "")
            else:
                # 使用 generate 端点
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                }
                resp = self.session.post(
                    f"{self.endpoint}/api/generate", json=payload, timeout=timeout
                )
                data = resp.json()
                return data.get("response", "")
        except Exception as e:
            print(f"LLM调用错误: {e}")
            return ""

    def generate_stream(
        self, prompt, model=None, provider=None, system=None, timeout=120
    ):
        """流式生成回复，支持 system prompt"""
        import json

        model = model or self.default_model

        try:
            if system:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": True,
                }
                resp = self.session.post(
                    f"{self.endpoint}/api/chat",
                    json=payload,
                    stream=True,
                    timeout=timeout,
                )
                for line in resp.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
            else:
                payload = {"model": model, "prompt": prompt, "stream": True}
                resp = self.session.post(
                    f"{self.endpoint}/api/generate",
                    json=payload,
                    stream=True,
                    timeout=timeout,
                )
                for line in resp.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            print(f"流式生成错误: {e}")
            yield f"错误: {e}"

    def generate_async(
        self, prompt, model=None, provider=None, system=None, timeout=120, callback=None
    ):
        """异步生成（后台线程）"""
        import threading

        def _generate():
            result = self.generate(prompt, model, provider, system, timeout)
            if callback:
                callback(result)
            return result

        thread = threading.Thread(target=_generate, daemon=True)
        thread.start()
        return thread


llm_manager = LLMManager()
