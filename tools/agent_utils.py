#!/usr/bin/env python3
"""Agent 工具函数"""

from typing import Dict


def make_response(content: str, **kwargs) -> Dict:
    """生成统一格式的 Agent 响应

    将 calculator_agent 和 analysis_agent 共用的 _resp 逻辑提取到此函数。

    Args:
        content: 响应文本内容
        **kwargs: 额外字段，如 output_type

    Returns:
        Dict: {"success": True, "response": content, "output_content": content, **kwargs}
    """
    return {"success": True, "response": content, "output_content": content, **kwargs}
