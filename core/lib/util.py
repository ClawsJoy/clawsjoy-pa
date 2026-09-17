# -*- coding: utf-8 -*-
"""P3-A 辅助函数归位：通用工具（从 agent_gateway_enhanced.py 迁入，2026-09-12）。"""
import json
from pathlib import Path


def _get_skeletons_by_type(module_type, user_id="default", session_id="default"):
    """从 world_model 中提取指定类型模块的骨架"""
    _state_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
    if not _state_file.exists():
        return None
    try:
        _state = json.loads(_state_file.read_text())
        _modules = _state.get("world_model", {}).get("modules", {})
        _skeletons = []
        for _fp, _info in _modules.items():
            if f"/{module_type}/" in _fp and _info.get("skeleton"):
                _skeletons.append(f"// {_fp}\n{_info['skeleton']}")
        return "\n\n".join(_skeletons[:3]) if _skeletons else None
    except Exception:
        return None
