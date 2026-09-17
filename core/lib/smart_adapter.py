#!/usr/bin/env python3
"""Smart Adapter - Smart Adapter 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import threading
import time
from pathlib import Path
from typing import Dict, Generator, Optional

import yaml

from core.lib.llm_manager import llm_manager


class SmartAdapter:
    """智能适配器 - 根据任务自动选择模型"""

    def __init__(self):
        self.config = self._load_config()
        self.default_model = self.config.get("default", {}).get("model", "qwen2.5:3b")
        self.default_provider = self.config.get("default", {}).get("provider", "ollama")
        self.default_timeout = self.config.get("performance", {}).get("timeout", 60)
        self.task_types = self.config.get("task_types", {})

    def _load_config(self) -> Dict:
        """加载配置"""
        config_paths = ["config/skills/smart_adapter.yaml", "config/smart_adapter.yaml"]
        for path in config_paths:
            if Path(path).exists():
                with open(path, "r") as f:
                    return yaml.safe_load(f) or {}
        print("⚠️ smart_adapter.yaml 未找到，使用默认配置")
        return {}

    def detect_task_type(self, text: str) -> str:
        """检测任务类型"""
        text_lower = text.lower()
        for task_type, task_config in self.task_types.items():
            keywords = task_config.get("keywords", [])
            for keyword in keywords:
                if keyword in text_lower:
                    return task_type
        return "qa"

    def _get_task_config(self, task_type: str) -> Dict:
        """获取任务配置"""
        task_config = self.task_types.get(task_type, {})
        return {
            "model": task_config.get("model", self.default_model),
            "provider": task_config.get("provider", self.default_provider),
            "temperature": task_config.get("temperature", 0.7),
            "max_tokens": task_config.get("max_tokens", 2000),
            "timeout": task_config.get("timeout", self.default_timeout),
            "system_prompt": task_config.get("system_prompt", ""),
        }

    def _sanitize_response(self, response: str, identity: str = "ClawsJoy") -> str:
        """安全过滤：防止 LLM 泄露身份"""
        # 禁止的关键词
        forbidden = [
            "Qwen",
            "千问",
            "阿里云",
            "阿里巴巴",
            "阿里",
            "通义",
            "Model",
            "AI model",
        ]
        for word in forbidden:
            if word in response:
                # 替换为 ClawsJoy 身份
                response = response.replace(word, identity)

        # 如果还是泄露，强制替换
        if "ClawsJoy" not in response and len(response) > 0:
            response = f"我是 {identity} 助手，很高兴为您服务！请问有什么可以帮您的？"

        return response

    def generate(
        self, prompt: str, auto_select: bool = True, system: str = None, **kwargs
    ) -> str:
        """生成响应（同步）- 带安全防护"""

        # 提取 system 参数
        if system is None:
            system = kwargs.get("system", None)

        # 优先级: kwargs中的model > Agent配置的model > 任务类型检测的model
        if "model" in kwargs:
            model = kwargs["model"]
            provider = kwargs.get("provider", self.default_provider)
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 2000)
            timeout = kwargs.get("timeout", self.default_timeout)
            task_type = "custom"
        elif auto_select:
            task_type = self.detect_task_type(prompt)
            config = self._get_task_config(task_type)
            model = config["model"]
            provider = config["provider"]
            temperature = config["temperature"]
            max_tokens = config["max_tokens"]
            timeout = config["timeout"]
            # 如果任务有默认 system prompt，合并
            if config.get("system_prompt") and not system:
                system = config["system_prompt"]
        else:
            model = kwargs.get("model", self.default_model)
            provider = kwargs.get("provider", self.default_provider)
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 2000)
            timeout = kwargs.get("timeout", self.default_timeout)
            task_type = "custom"

        print(f"🤖 选择模型: {provider}/{model} (超时: {timeout}s)")

        # 默认 system prompt（安全兜底）
        if system is None:
            system = "你是 ClawsJoy 助手。你的名字是 ClawsJoy 助手。你不是 Qwen、千问或任何其他模型。"

        try:
            result = llm_manager.generate(
                prompt=prompt,
                model=model,
                provider=provider,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                system=system,
            )
            # 安全过滤
            return self._sanitize_response(result)
        except Exception as e:
            print(f"LLM调用错误: {e}")
            return f"抱歉，我暂时无法回答这个问题。请稍后再试。"

    def generate_stream(
        self, prompt: str, auto_select: bool = True, system: str = None, **kwargs
    ) -> Generator:
        """流式生成响应 - 带安全防护"""

        if system is None:
            system = kwargs.get("system", None)

        if auto_select:
            task_type = self.detect_task_type(prompt)
            config = self._get_task_config(task_type)
            model = config["model"]
            provider = config["provider"]
            temperature = config["temperature"]
            max_tokens = config["max_tokens"]
            timeout = config["timeout"]
            if config.get("system_prompt") and not system:
                system = config["system_prompt"]
        else:
            model = kwargs.get("model", self.default_model)
            provider = kwargs.get("provider", self.default_provider)
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 2000)
            timeout = kwargs.get("timeout", self.default_timeout)

        print(f"🤖 流式生成: {provider}/{model}")

        if system is None:
            system = "你是 ClawsJoy 助手。你的名字是 ClawsJoy 助手。"

        full_response = ""
        try:
            for chunk in llm_manager.generate_stream(
                prompt=prompt,
                model=model,
                provider=provider,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                system=system,
            ):
                full_response += chunk
                yield chunk
        except Exception as e:
            print(f"流式生成错误: {e}")
            yield f"生成失败: {e}"

    def _sanitize_response(self, response: str, identity: str = "ClawsJoy") -> str:
        """安全过滤：防止 LLM 泄露身份"""
        # 1. 替换关键词
        forbidden = [
            "Qwen",
            "千问",
            "阿里云",
            "阿里巴巴",
            "通义",
            "Model",
            "AI model",
            "语言模型",
        ]
        for word in forbidden:
            if word in response:
                response = response.replace(word, identity)

        # 2. 如果完全没有 ClawsJoy，且长度合适，强制添加身份
        if "ClawsJoy" not in response and len(response) > 0:
            # 保留原回答，但前面加上身份声明
            response = f"（我是 ClawsJoy 助手）{response}"

        # 3. 极端情况：回答全是敏感词，替换为默认回答
        if any(word in response for word in ["Qwen", "千问"]) and len(response) < 50:
            return "我是 ClawsJoy 助手，很高兴为您服务！请问有什么可以帮您的？"

        return response

    # 全局实例


smart_adapter = SmartAdapter()
