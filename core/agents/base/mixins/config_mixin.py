#!/usr/bin/env python3
"""配置系统 Mixin - 修复版"""

from pathlib import Path
from typing import Any, Dict

import yaml

from core.lib.config_helper import get_data_root
from core.lib.unified_config import unified_config


class ConfigMixin:
    """配置系统混入类"""

    def _load_config(self):
        """加载配置（支持多级覆盖）"""
        # 1. 全局默认配置
        default_config = self._get_default_config()

        # 2. Agent 特定配置
        agent_config = self._load_agent_config()

        # 3. 用户级配置
        user_config = self._load_user_config()

        # 合并配置（用户 > Agent > 默认）
        self._config = self._deep_merge(default_config, agent_config or {})
        self._config = self._deep_merge(self._config, user_config or {})

    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "enabled": True,
            "timeout": 30,
            "max_retries": 3,
            "memory_enabled": True,
            "learning_enabled": True,
            "model": unified_config.get("llm.default_model", "qwen2.5:7b-instruct-q4_0-gpu"),
            "ollama_url": unified_config.get("llm.endpoint", "http://localhost:11434"),
        }

    def _load_agent_config(self) -> Dict:
        """加载 Agent 配置"""
        config_file = (
            Path(__file__).parent.parent.parent
            / "config"
            / "agents"
            / f"{self.name}.yaml"
        )
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    data = yaml.safe_load(f)
                    return data if data is not None else {}
            except Exception:
                pass
        return {}

    def _load_user_config(self) -> Dict:
        """加载用户配置"""
        user_config_file = Path(f"{get_data_root()}/users/{self.user_id}/config.yaml")
        if user_config_file.exists():
            try:
                with open(user_config_file, "r") as f:
                    config = yaml.safe_load(f)
                    if config and self.name in config:
                        return config[self.name]
            except Exception:
                pass
        return {}

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """深度合并字典（安全版本）"""
        if base is None:
            base = {}
        if override is None:
            override = {}

        result = base.copy()
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get_config(self, key: str = None, default: Any = None) -> Any:
        """获取配置"""
        if key is None:
            return self._config
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def update_config(self, updates: Dict):
        """更新配置"""
        self._config = self._deep_merge(self._config, updates)
        self._save_user_config()

    def _save_user_config(self):
        """保存用户配置"""
        user_config_file = Path(f"{get_data_root()}/users/{self.user_id}/config.yaml")
        user_config_file.parent.mkdir(parents=True, exist_ok=True)

        existing = {}
        if user_config_file.exists():
            try:
                with open(user_config_file, "r") as f:
                    existing = yaml.safe_load(f) or {}
            except Exception:
                pass

        existing[self.name] = self._config
        with open(user_config_file, "w") as f:
            yaml.dump(existing, f)

    def reload_config(self):
        """重载配置"""
        self._load_config()
