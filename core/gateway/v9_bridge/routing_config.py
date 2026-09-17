# -*- coding: utf-8 -*-
"""P3-A 辅助函数归位：_load_v9_routing_config（从 agent_gateway_enhanced.py 迁入，2026-09-12）。"""
from pathlib import Path

import yaml


def _load_v9_routing_config():
    """#166 加载 config/v9/message_routing.yaml 路由配置，失败返回 {}。"""
    try:
        _p = Path("config/v9/message_routing.yaml")
        if not _p.exists():
            return {}
        with open(_p, "r", encoding="utf-8") as _f:
            return yaml.safe_load(_f) or {}
    except Exception as _e:
        print(f"[ROUTING] V9 routing config 加载失败: {_e}")
        return {}
