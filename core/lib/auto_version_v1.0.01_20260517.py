#!/usr/bin/env python3
"""Auto Version V1.0.01 20260517 - Auto Version V1.0.01 20260517 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""自动版本装饰器 - 让每个模块自动获取版本号"""

import functools
from pathlib import Path

from core.lib.version_registry_v1_0_01_20260517 import version_registry


def auto_version(module_name: str, module_path: str = None):
    """自动版本装饰器：为模块自动注入版本号"""

    def decorator(cls_or_func):
        # 自动注册并获取版本
        if module_path:
            reg_info = version_registry.register_module(module_name, module_path)
            version = reg_info["version"]
        else:
            version = version_registry.get_version(module_name) or "v0.0.00"

        # 注入版本属性
        if hasattr(cls_or_func, "__version__"):
            cls_or_func.__version__ = version

        @functools.wraps(cls_or_func)
        def wrapper(*args, **kwargs):
            return cls_or_func(*args, **kwargs)

        wrapper.__version__ = version
        return wrapper

    return decorator


class VersionedModule:
    """版本化模块基类 - 继承即可获得自动版本"""

    @property
    def version(self):
        return getattr(self, "__version__", "v0.0.00")

    @classmethod
    def get_version(cls):
        return getattr(cls, "__version__", "v0.0.00")


# 使用示例:
# @auto_version("my_module", "path/to/my_module.py")
# class MyModule(VersionedModule):
#     pass
