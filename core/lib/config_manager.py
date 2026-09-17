#!/usr/bin/env python3
"""Config Manager - Config Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""统一配置管理器 - 替代所有 get_config 调用"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ConfigManager:
    """统一配置管理器 - 单例模式"""

    _instance = None
    _config: Dict = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        """加载所有配置"""
        config_file = Path(__file__).parent.parent / "config/driver/unified.yaml"
        if config_file.exists():
            with open(config_file, "r") as f:
                self._config = unified_config.get("config_manager", {})
        else:
            self._config = self._default_config()

    def _default_config(self) -> Dict:
        return {
            "services": {"ports": {"gateway": 5002}},
            "llm": {
                "ollama": {
                    "model": unified_config.get_llm_config().get(
                        "fast_model",
                        unified_config.get_llm_config().get(
                            "fast_model",
                            unified_config.get(
                                "llm.fast_model", get_llm_model(fast=True)
                            ),
                        ),
                    ),
                    "timeout": 30,
                }
            },
            "thresholds": {"success_rate": {"high": 0.9}},
        }

    @lru_cache(maxsize=128)
    def get(self, path: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔"""
        parts = path.split(".")
        value = self._config
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
                if value is None:
                    return default
            else:
                return default
        return value

    def get_port(self, service: str) -> int:
        """获取服务端口"""
        return self.get(f"services.ports.{service}", 5000)

    def get_model(self) -> str:
        """获取默认模型"""
        return self.get("llm.ollama.model", "qwen2.5:3b")

    def get_timeout(self, timeout_type: str = "normal") -> int:
        """获取超时配置"""
        return self.get(f"orchestrator.{timeout_type}_timeout", 30)

    def get_limit(self, limit_type: str) -> int:
        """获取限制配置"""
        return self.get(f"capacity.{limit_type}", 100)

    def get_threshold(self, category: str, name: str) -> float:
        """获取阈值"""
        return self.get(f"{category}.{name}", 0.5)

    def reload(self):
        """重新加载配置"""
        self._config = None
        self.get.cache_clear()
        self._load()


config_manager = ConfigManager()


if __name__ == "__main__":
    print("统一配置管理器测试")
    print(f"网关端口: {config_manager.get_port('gateway')}")
    print(f"默认模型: {config_manager.get_model()}")
    print(f"正常超时: {config_manager.get_timeout('normal')}s")
    print(f"事件队列大小: {config_manager.get_limit('event_queue_maxlen')}")
    print(f"高成功率阈值: {config_manager.get_threshold('success_rate', 'high')}")

# ========== 热重载支持 ==========
import time
from pathlib import Path


class ConfigHotReload:
    """配置热重载管理器"""

    def __init__(self):
        self.config_file = Path(__file__).parent.parent / "config/driver/unified.yaml"
        self.last_mtime = (
            self.config_file.stat().st_mtime if self.config_file.exists() else 0
        )
        self.watchers = []

    def check_and_reload(self) -> bool:
        """检查配置文件是否变更，如有则重载"""
        if not self.config_file.exists():
            return False

        current_mtime = self.config_file.stat().st_mtime
        if current_mtime > self.last_mtime:
            self.last_mtime = current_mtime
            config_manager.reload()
            self._notify_watchers()
            return True
        return False

    def watch(self, callback):
        """注册变更回调"""
        self.watchers.append(callback)

    def _notify_watchers(self):
        for callback in self.watchers:
            try:
                callback()
            except Exception as e:
                print(f"回调执行失败: {e}")

    def start_background_watch(self, interval: int = 5):
        """启动后台监控线程"""
        import threading

        def watch_loop():
            while True:
                self.check_and_reload()
                time.sleep(interval)

        thread = threading.Thread(target=watch_loop, daemon=True)
        thread.start()
        return thread


# 添加热重载方法到 ConfigManager
def hot_reload_enabled(self) -> bool:
    """启用热重载"""
    if not hasattr(ConfigManager, "_hot_reload"):
        ConfigManager._hot_reload = ConfigHotReload()
    return True


def check_reload(self) -> bool:
    """检查是否需要重载"""
    if hasattr(ConfigManager, "_hot_reload"):
        return ConfigManager._hot_reload.check_and_reload()
    return False


ConfigManager.hot_reload_enabled = hot_reload_enabled
ConfigManager.check_reload = check_reload

# 全局热重载实例
config_hot_reload = ConfigHotReload()


if __name__ == "__main__":
    print("热重载测试:")
    print(f"配置文件: {config_hot_reload.config_file}")
    print(f"最后修改时间: {config_hot_reload.last_mtime}")
# DEPRECATED: 请使用 unified_config 代替
