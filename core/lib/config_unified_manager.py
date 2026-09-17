#!/usr/bin/env python3
"""Config Unified Manager - Config Unified Manager 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ConfigUnifiedManager:
    """配置统一管理器"""

    _instance = None
    _config: Dict = {}
    _config_sources: Dict[str, str] = {}  # 配置键 -> 源文件

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        """初始化，加载所有配置"""
        self._load_all_configs()
        self._register_watchers()

    def _load_all_configs(self):
        """加载所有配置文件，统一合并"""

        # 1. 先加载统一配置（优先级最低）
        unified_path = Path("config/unified.yaml")
        if unified_path.exists():
            self._merge_config(unified_path, priority=1)

        # 2. 加载系统配置
        self._load_yaml_dir("config/system", priority=2)

        # 3. 加载 LLM 配置（优先级覆盖）
        self._load_yaml_dir("config/llm", priority=3)

        # 4. 加载安全配置
        self._load_yaml_dir("config/security", priority=3)

        # 5. 加载向量配置
        self._load_yaml_dir("config/vector", priority=3)

        # 6. 加载路由配置
        self._load_yaml_dir("config/routes", priority=3)

        # 7. 加载管家配置
        self._load_yaml_dir("config/butler", priority=3)

        # 8. 最后加载 driver 配置（最高优先级，覆盖其他）
        self._load_yaml_dir("config/driver", priority=4)

    def _load_yaml_dir(self, dir_path: str, priority: int):
        """加载目录下所有 YAML 文件"""
        path = Path(dir_path)
        if not path.exists():
            return

        for yaml_file in path.glob("*.yaml"):
            self._merge_config(yaml_file, priority)

    def _merge_config(self, config_file: Path, priority: int):
        """合并配置文件"""
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data:
                return

            self._deep_merge(self._config, data, priority, str(config_file))
            print(f"[配置] 加载: {config_file} (优先级:{priority})")

        except Exception as e:
            print(f"[配置] 加载失败 {config_file}: {e}")

    def _deep_merge(self, target: Dict, source: Dict, priority: int, source_file: str):
        """深度合并配置，高优先级覆盖低优先级"""
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_merge(target[key], value, priority, source_file)
            else:
                # 记录配置来源
                self._config_sources[f"{key}"] = f"{source_file} (p:{priority})"
                target[key] = value

    def _register_watchers(self):
        """注册配置监听器"""
        try:
            from core.lib.config_watcher import config_watcher

            # 监听所有配置目录
            watch_dirs = [
                "config/system",
                "config/llm",
                "config/security",
                "config/vector",
                "config/routes",
                "config/butler",
                "config/driver",
            ]

            for watch_dir in watch_dirs:
                path = Path(watch_dir)
                if path.exists():
                    for yaml_file in path.glob("*.yaml"):
                        config_watcher.register(str(yaml_file), self._reload_config)

            config_watcher.start()
            print("✅ 配置热重载监听已启动")

        except Exception as e:
            print(f"⚠️ 配置监听器启动失败: {e}")

    def _reload_config(self):
        """重新加载配置"""
        print("🔄 检测到配置变化，重新加载...")
        old_config = self._config.copy()
        self._config = {}
        self._load_all_configs()
        print("✅ 配置重新加载完成")

    def get(self, key: str, default=None):
        """获取配置值（支持点号路径）"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value if value is not None else default

    def get_all(self) -> Dict:
        """获取所有配置"""
        return self._config

    def get_source(self, key: str) -> Optional[str]:
        """获取配置来源"""
        return self._config_sources.get(key)

    def print_summary(self):
        """打印配置摘要"""
        print("\n📋 配置摘要:")
        print(f"   总配置项: {len(self._config)}")
        print(f"   主要配置:")
        for key in ["system", "llm", "services", "security", "vector"]:
            if key in self._config:
                print(f"      - {key}: {list(self._config[key].keys())[:3]}...")

    # 配置路径别名（兼容旧代码）
    def get_port(self, service: str = "gateway") -> int:
        """获取服务端口"""
        ports = self.get("services", {})
        if isinstance(ports, dict):
            service_config = ports.get(service, {})
            if isinstance(service_config, dict):
                return service_config.get("port", 5002)
            elif isinstance(service_config, int):
                return service_config
        return 5002

    def get_llm_config(self) -> Dict:
        """获取 LLM 配置"""
        llm = self.get("llm", {})
        return {
            "provider": llm.get("provider", "ollama"),
            "model": llm.get("model", "qwen2.5:3b"),
            "endpoint": llm.get(
                "endpoint", unified_config.get("llm.endpoint", "http://localhost:11434")
            ),
        }

        # 全局实例


config_manager = ConfigUnifiedManager()
