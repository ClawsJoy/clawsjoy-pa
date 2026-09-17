#!/usr/bin/env python3
"""Output Filter - Output Filter 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""输出过滤器 - 剥离泄漏的推理文本"""
import re


class OutputFilter:
    PATTERNS = [
        (r"^(Reasoning:|Let me|I will|Now I|First, let me).*$", ""),
        (r"让我想想|我来分析|我需要", ""),
    ]

    @classmethod
    def filter(cls, text: str) -> str:
        for pattern, replacement in cls.PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
        return text.strip()
