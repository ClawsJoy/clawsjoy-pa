from core.lib.unified_config import unified_config

"""动态阈值调整器 - 统一入口"""

import importlib.util
from pathlib import Path


def _get_latest():
    lib_dir = Path(__file__).parent
    versions = []
    for f in lib_dir.glob("dynamic_threshold_v*.py"):
        if f.name.startswith("dynamic_threshold_v"):
            versions.append(f)
    if not versions:
        raise ImportError("未找到 dynamic_threshold 模块")
    versions.sort(reverse=True)
    spec = importlib.util.spec_from_file_location("threshold_module", versions[0])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_module = _get_latest()
dynamic_threshold = _module.dynamic_threshold
DynamicThreshold = _module.DynamicThreshold

__all__ = ["dynamic_threshold", "DynamicThreshold"]
