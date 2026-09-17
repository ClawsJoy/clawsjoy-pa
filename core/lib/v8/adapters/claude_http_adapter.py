#!/usr/bin/env python3
"""Claude HTTP 适配器 — 基于 Anthropic Messages API"""

import json
import os

import requests

from . import BaseAdapter


class ClaudeHTTPAdapter(BaseAdapter):
    """Anthropic Messages API 适配器（支持 stream / 非 stream 两种模式）

    端点: https://api.anthropic.com/v1/messages
    api_key 优先级: 参数 > 环境变量 ANTHROPIC_API_KEY
    """

    endpoint = "https://api.anthropic.com/v1/messages"
    api_version = "2023-06-01"
    supports_stream = True

    def __init__(self, api_key: str = "", model: str = "claude-3-opus", **kwargs):
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        super().__init__(api_key=api_key, model=model, **kwargs)

    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json",
        }

    def _build_messages(self, prompt: str, system_prompt: str = "", history: list = None):
        """构造 Anthropic 消息格式，返回 (system, messages)"""
        system = system_prompt or None
        messages = []
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        return system, messages

    def _parse_content(self, data: dict) -> str:
        """从 Messages API 非流式响应中提取文本内容"""
        parts = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "thinking":
                parts.append(block.get("thinking", ""))
        return "\n".join(parts)

    def execute(self, prompt: str, system_prompt: str = "", history: list = None,
                max_tokens: int = 4096, temperature: float = 0.7, **kwargs) -> dict:
        """非流式调用 Messages API"""
        system, messages = self._build_messages(prompt, system_prompt, history)
        body = {
            "model": self.model or "claude-3-opus",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            body["system"] = system
        if kwargs:
            body.update(kwargs)

        try:
            resp = requests.post(self.endpoint, headers=self._headers(), json=body, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                content = self._parse_content(data)
                usage = data.get("usage", {})
                tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                return {"success": True, "content": content, "tokens": tokens, "model": self.model}
            return {"success": False, "content": f"API错误: {resp.status_code} {resp.text[:500]}",
                    "tokens": 0, "model": self.model}
        except Exception as e:
            return {"success": False, "content": f"请求失败: {e}", "tokens": 0, "model": self.model}

    def execute_stream(self, prompt: str, system_prompt: str = "", history: list = None,
                       max_tokens: int = 4096, temperature: float = 0.7, **kwargs):
        """流式调用 Messages API，逐段 yield 文本增量。

        yield 结构:
          {"success": True, "content": str, "delta": True, "model": str}          文本增量
          {"success": True, "content": "", "delta": False, "tokens": int, "done": True}  结束事件
          {"success": False, "content": str, "tokens": 0, "model": str}           错误
        """
        system, messages = self._build_messages(prompt, system_prompt, history)
        body = {
            "model": self.model or "claude-3-opus",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if system:
            body["system"] = system
        if kwargs:
            body.update(kwargs)

        try:
            resp = requests.post(self.endpoint, headers=self._headers(), json=body,
                                 stream=True, timeout=120)
            if resp.status_code != 200:
                yield {"success": False, "content": f"API错误: {resp.status_code} {resp.text[:200]}",
                       "tokens": 0, "model": self.model}
                return

            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data:"):
                    line = line[5:].strip()
                if line == "[DONE]":
                    break
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type")
                if event_type == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        yield {"success": True, "content": delta.get("text", ""),
                               "delta": True, "model": self.model}
                elif event_type == "message_delta":
                    usage = event.get("usage", {})
                    yield {"success": True, "content": "", "delta": False,
                           "tokens": usage.get("output_tokens", 0),
                           "model": self.model, "done": True}
        except Exception as e:
            yield {"success": False, "content": f"请求失败: {e}", "tokens": 0, "model": self.model}

    def execute_json(self, prompt: str, system_prompt: str = "") -> dict:
        """JSON Output 模式：要求模型只输出合法 JSON 并解析"""
        sys_prompt = system_prompt or (
            "你是一个 JSON 输出助手。只输出合法的 JSON 对象，"
            "不要包含任何解释或 Markdown 代码块标记。"
        )
        result = self.execute(prompt=prompt, system_prompt=sys_prompt,
                              max_tokens=800, temperature=0.2)
        if not result.get("success"):
            return result

        content = result.get("content", "").strip()
        # 去除可能的 Markdown 代码块围栏
        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)
        try:
            return {"success": True, "content": json.loads(content),
                    "tokens": result.get("tokens", 0), "model": self.model}
        except json.JSONDecodeError as e:
            return {"success": False, "content": f"JSON 解析失败: {e}",
                    "tokens": result.get("tokens", 0), "model": self.model}
