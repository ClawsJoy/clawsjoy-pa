#!/usr/bin/env python3
"""适配器工厂 — 根据模型名返回对应适配器"""

from core.lib.v8.adapters.deepseek_adapter import DeepSeekAdapter
from core.lib.v8.adapters.claude_code_adapter import ClaudeCodeAdapter


def get_adapter(model: str, api_key: str = "", **kwargs):
    """
    根据模型名返回适配器实例。
    model: "deepseek-v3" | "claude-code" | "claude-4" | "dalle" | "ollama" | 等
    """
    if not model or model.lower() in ("ollama", "qwen", "clawsjoy", ""):
        from core.lib.v8.adapters.clawsjoy_adapter import ClawsJoyAdapter
        agent_name = kwargs.get("agent_name", "chat_agent_v4")
        return ClawsJoyAdapter(agent_name=agent_name, model="ollama")
    model_lower = model.lower()
        
    if "glm" in model_lower:
        return DeepSeekAdapter(
            api_key=api_key,
            model=kwargs.pop("model", model if model_lower != "glm" else "glm-5.2"),
            endpoint="https://api.z.ai/api/paas/v4/chat/completions",
            **kwargs
        )
    elif "deepseek" in model_lower:
        return DeepSeekAdapter(api_key=api_key, model=model, **kwargs)

    elif "claude-code" in model_lower or "claude_cli" in model_lower:
        return ClaudeCodeAdapter(api_key=api_key, model="claude-code", **kwargs)

    elif "claude" in model_lower:
        # Claude API（Anthropic Messages API HTTP 版本）
        from core.lib.v8.adapters.claude_http_adapter import ClaudeHTTPAdapter
        return ClaudeHTTPAdapter(api_key=api_key, model=model, **kwargs)

    elif "dalle" in model_lower or "dall-e" in model_lower:
        # TODO: DALL-E 适配器
        return None

    elif "ollama" in model_lower or "qwen" in model_lower:
        from core.lib.v8.adapters.clawsjoy_adapter import ClawsJoyAdapter
        return ClawsJoyAdapter(agent_name=kwargs.get("agent_name", "chat_agent_v4"), model=model)

    else:
        # 未知模型，尝试用 OpenAI 兼容格式
        return DeepSeekAdapter(api_key=api_key, model=model, **kwargs)
