#!/usr/bin/env python3
"""Output Filter V1 - Output Filter V1 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""输出过滤器 v1.0.0 - 剥离 LLM 泄漏的推理文本"""

import re
from typing import List, Optional, Tuple


class OutputFilter:
    """过滤 LLM 输出，确保输出稳定"""

    VERSION = "1.0.0"

    # 需要剥离的推理模式
    REASONING_PATTERNS = [
        # 英文推理模式
        (r"^(Reasoning|Let me|I will|Now I|First, let me|Here is|I think).*$", ""),
        (r"^(Wait|Actually|By the way|Note that).*$", ""),
        (r"^(In order to|To accomplish|Based on).*$", ""),
        # 中文推理模式
        (r"^(让我想想|我来分析|我需要|首先|接下来|然后|最后).*$", ""),
        (r"^(根据|基于|为了|通过|从).*$", ""),
        (r"^(思考|分析|推理|计划).*$", ""),
        (r"^(好的|明白了|知道了|OK).*$", ""),
    ]

    # 需要清理的工具调用泄漏
    TOOL_LEAK_PATTERNS = [
        (r"```tool_code\n.*?\n```", ""),
        (r"<function=.*?</function>", ""),
        (r'\{[^{]*"function"[^}]*\}', ""),
    ]

    # 需要清理的 Thinking 标签
    THINKING_TAGS = [
        (r"<thinking>.*?</thinking>", ""),
        (r"<thought>.*?</thought>", ""),
        (r"```thought\n.*?\n```", ""),
    ]

    @classmethod
    def filter(cls, text: str) -> str:
        """过滤输出文本"""
        if not text:
            return text

        original = text
        filtered = text

        # 1. 逐行过滤推理内容
        lines = filtered.split("\n")
        filtered_lines = []
        for line in lines:
            should_keep = True
            for pattern, _ in cls.REASONING_PATTERNS:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    should_keep = False
                    break
            if should_keep:
                filtered_lines.append(line)
        filtered = "\n".join(filtered_lines)

        # 2. 移除工具调用泄漏
        for pattern, replacement in cls.TOOL_LEAK_PATTERNS:
            filtered = re.sub(
                pattern, replacement, filtered, flags=re.DOTALL | re.IGNORECASE
            )

        # 3. 移除 thinking 标签
        for pattern, replacement in cls.THINKING_TAGS:
            filtered = re.sub(
                pattern, replacement, filtered, flags=re.DOTALL | re.IGNORECASE
            )

        # 4. 清理多余空行
        filtered = re.sub(r"\n{3,}", "\n\n", filtered)
        filtered = filtered.strip()

        return filtered

    @classmethod
    def has_reasoning(cls, text: str) -> bool:
        """检查是否包含推理文本"""
        for pattern, _ in cls.REASONING_PATTERNS:
            if re.match(pattern, text.strip(), re.IGNORECASE):
                return True
        return False

    @classmethod
    def extract_json(cls, text: str) -> Optional[str]:
        """提取 JSON 内容"""
        # 查找 JSON 块
        json_patterns = [
            r"```json\n(.*?)\n```",
            r"```\n(\{.*?\})\n```",
            r"(\{.*\})",
        ]

        for pattern in json_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1)
        return None


# 测试
if __name__ == "__main__":
    test_cases = [
        "Reasoning: Let me think about this...\nHere is the answer: 42",
        "让我想想怎么回答...\n答案是 42",
        '```json\n{"result": 42}\n```',
        "好的，我知道了。结果是 42。",
    ]

    print("输出过滤器测试")
    print("=" * 40)
    for text in test_cases:
        filtered = OutputFilter.filter(text)
        print(f"\n原文本: {text[:50]}...")
        print(f"过滤后: {filtered[:50]}...")
