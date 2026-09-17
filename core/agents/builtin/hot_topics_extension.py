#!/usr/bin/env python3
"""Hot Topics Extension - Hot Topics Extension 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import logging

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)

"""热门话题扩展 - 独立模块，不破坏原分析师"""
import json
from pathlib import Path
from typing import Dict, List


class HotTopicsExtension:
    """热门话题扩展"""

    @staticmethod
    def get_analytics() -> Dict:
        """获取热门话题分析"""
        result = {"hot_signals": [], "summary": {"total": 0, "top_keywords": []}}

        signals_file = Path(f"{get_data_root()}/hot_db/hot_signals.json")
        if signals_file.exists():
            try:
                with open(signals_file, "r") as f:
                    data = json.load(f)
                signals = data.get("signals", data) if isinstance(data, dict) else data
                if isinstance(signals, list):
                    result["hot_signals"] = signals[:20]
                    result["summary"]["total"] = len(signals)

                    # 统计关键词热度
                    keyword_heat = {}
                    for s in signals:
                        kw = s.get("keyword", "未知")
                        heat = s.get("热度", 0)
                        keyword_heat[kw] = keyword_heat.get(kw, 0) + heat

                    top = sorted(
                        keyword_heat.items(), key=lambda x: x[1], reverse=True
                    )[:10]
                    result["summary"]["top_keywords"] = [
                        {"keyword": k, "heat": v} for k, v in top
                    ]
            except Exception as e:
                print(f"读取热门话题失败: {e}")

        return result


hot_topics = HotTopicsExtension()
