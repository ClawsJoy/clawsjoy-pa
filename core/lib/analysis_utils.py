#!/usr/bin/env python3
"""Analysis Utils - Analysis Utils 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import json

from core.lib.memory_simple import memory
from core.lib.unified_config import unified_config


def get_latest_analysis():
    """获取最新的分析结果"""
    # 尝试多个分类
    categories = ["analysis_result", "intelligence_analysis", "unified_analysis"]
    for cat in categories:
        items = memory.recall_all(category=cat)
        for item in reversed(items):
            try:
                return json.loads(item)
            except Exception as e:
                continue
    return None
