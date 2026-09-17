#!/usr/bin/env python3
"""真实 LLM 对话"""

import json

import requests

from core.lib.unified_config import unified_config


def get_llm_response(
    message: str, user_id: str = "guest", memories: list = None
) -> str:
    """调用真实 LLM 获取响应"""
    endpoint = unified_config.get("llm.endpoint", "http://localhost:11434")
    model = unified_config.get("llm.default_model", "qwen2.5:3b")

    # 构建 prompt（包含记忆上下文）
    context = ""
    if memories:
        context = f"用户之前的偏好: {', '.join(memories[:3])}\n\n"

    prompt = f"{context}用户说: {message}\n请友好回复。"

    try:
        response = requests.post(
            f"{endpoint}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 256,
            },
            timeout=30,
        )
        if response.status_code == 200:
            return response.json().get("response", message)
        else:
            return f"LLM 服务异常: {response.status_code}"
    except Exception as e:
        return f"LLM 调用失败: {e}"


def translate_text(text: str, target: str = "zh") -> str:
    """真实翻译"""
    endpoint = unified_config.get("llm.endpoint", "http://localhost:11434")
    model = unified_config.get("llm.default_model", "qwen2.5:3b")

    prompt = f"将以下英文翻译成中文，只输出翻译结果：\n{text}"

    try:
        response = requests.post(
            f"{endpoint}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=30,
        )
        if response.status_code == 200:
            return response.json().get("response", text)
        return text
    except Exception as e:
        return text
