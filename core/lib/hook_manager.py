#!/usr/bin/env python3
"""Hook Manager - Hook Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""钩子管理器 v2.0 - 配置驱动，消除硬编码"""

import importlib
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from core.lib.unified_config import unified_config


@dataclass
class Hook:
    """钩子定义"""

    name: str
    handler: str
    module: str
    function: str
    priority: int
    enabled: bool
    config: Dict = field(default_factory=dict)
    _func: Optional[Callable] = field(default=None, repr=False)


class HookManager:
    """配置驱动的钩子管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载钩子配置"""
        config_file = Path("config/hooks.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                self.config = unified_config.get("hooks", {})
        else:
            self.config = {}

        self._hooks = {}
        self._load_all_hooks()

    def _load_all_hooks(self):
        """加载所有钩子"""
        # 加载事件钩子
        for event_name, hooks in self.config.get("events", {}).items():
            self._hooks[f"event:{event_name}"] = self._parse_hooks(hooks, "events")

        # 加载数据钩子
        for data_stage, hooks in self.config.get("data", {}).items():
            self._hooks[f"data:{data_stage}"] = self._parse_hooks(hooks, "data")

        # 加载请求钩子
        for req_stage, hooks in self.config.get("request", {}).items():
            self._hooks[f"request:{req_stage}"] = self._parse_hooks(hooks, "request")

        # 加载学习钩子
        for learn_stage, hooks in self.config.get("learning", {}).items():
            self._hooks[f"learning:{learn_stage}"] = self._parse_hooks(
                hooks, "learning"
            )

        # 加载安全钩子
        for sec_stage, hooks in self.config.get("security", {}).items():
            self._hooks[f"security:{sec_stage}"] = self._parse_hooks(hooks, "security")

    def _parse_hooks(self, hooks_config: List[Dict], category: str) -> List[Hook]:
        """解析钩子配置"""
        hooks = []
        for h in hooks_config:
            try:
                # 获取 handler 或 module.function
                if "handler" in h:
                    handler_path = h["handler"]
                    if "." in handler_path:
                        module_path, func_name = handler_path.rsplit(".", 1)
                    else:
                        module_path = f"core.agents.{handler_path.split('._')[0]}"
                        func_name = handler_path
                elif "module" in h and "function" in h:
                    module_path = h["module"]
                    func_name = h["function"]
                else:
                    print(f"⚠️ 钩子配置格式错误: {h.get('name')}")
                    continue

                # 尝试导入模块
                try:
                    module = importlib.import_module(module_path)
                    func = getattr(module, func_name, None)

                    if func is None:
                        print(f"⚠️ 函数不存在: {module_path}.{func_name}")
                        continue

                    hook = Hook(
                        name=h["name"],
                        handler=h.get("handler", f"{module_path}.{func_name}"),
                        module=module_path,
                        function=func_name,
                        priority=h.get("priority", 10),
                        enabled=h.get("enabled", True),
                        config=h.get("config", {}),
                        _func=func,
                    )
                    hooks.append(hook)
                    print(f"  ✅ 钩子加载: {h['name']} -> {module_path}.{func_name}")
                except ImportError as e:
                    print(f"  ⚠️ 模块导入失败 {module_path}: {e}")
                    continue

            except Exception as e:
                print(f"  ❌ 钩子加载失败 {h.get('name')}: {e}")

        # 按优先级排序
        hooks.sort(key=lambda x: x.priority)
        return hooks

    def trigger(self, hook_path: str, context: Dict) -> Dict:
        """触发钩子"""
        hooks = self._hooks.get(hook_path, [])
        result = context

        for hook in hooks:
            if not hook.enabled:
                continue

            try:
                if hook._func:
                    # 调用钩子函数
                    if hook.config:
                        result = hook._func(result, **hook.config)
                    else:
                        result = hook._func(result)
                    print(f"  ✅ 钩子执行: {hook_path}/{hook.name}")
            except Exception as e:
                print(f"  ❌ 钩子失败: {hook_path}/{hook.name}: {e}")

        return result

    def get_hooks(self, hook_path: str = None) -> Dict:
        """获取钩子列表"""
        if hook_path:
            return self._hooks.get(hook_path, [])
        return self._hooks

    def get_stats(self) -> Dict:
        """获取钩子统计"""
        total = 0
        enabled = 0
        for hooks in self._hooks.values():
            total += len(hooks)
            enabled += sum(1 for h in hooks if h.enabled)
        return {"total": total, "enabled": enabled}


# 全局实例
hook_manager = HookManager()
