#!/usr/bin/env python3
"""Config Compat - Config Compat 模块

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

"""配置兼容层 - 保持原有代码正常工作"""

from pathlib import Path

import yaml


class ConfigCompat:
    """配置兼容层：优先从新位置读取，fallback到旧位置"""

    # 配置映射：旧路径 -> 新路径
    MAPPING = {
        "config/agent_lifecycle.yaml": f"{get_data_root()}/system/lifecycle/config.yaml",
        "config/agent_meeting.yaml": f"{get_data_root()}/system/meeting/config.yaml",
        "config/agent_skins.yaml": f"{get_data_root()}/system/skins/config.yaml",
        "config/butler_club.yaml": f"{get_data_root()}/system/butler_club/config.yaml",
        "config/agent_products.yaml": f"{get_data_root()}/marketplace/products.yaml",
        "config/butler/scriptbook.yaml": f"{get_data_root()}/system/agents/personal_butler/scriptbook.yaml",
        "config/agents_soul/agents_soul.yaml": f"{get_data_root()}/system/agents/personal_butler/soul.yaml",
    }

    @classmethod
    def get_config(cls, old_path: str):
        """获取配置文件，自动路由到新位置"""
        # 检查映射
        if old_path in cls.MAPPING:
            new_path = cls.MAPPING[old_path]
            if Path(new_path).exists():
                with open(new_path, "r") as f:
                    return yaml.safe_load(f)

        # fallback到原路径
        if Path(old_path).exists():
            with open(old_path, "r") as f:
                return yaml.safe_load(f)

        return {}

    @classmethod
    def get_agent_config(cls, agent_name: str, config_type: str = "config"):
        """获取Agent配置"""
        # 优先从新位置读取
        new_path = Path(
            f"{get_data_root()}/system/agents/{agent_name}/{config_type}.yaml"
        )
        if new_path.exists():
            with open(new_path, "r") as f:
                return yaml.safe_load(f)

        # fallback到全局配置
        old_path = Path(f"config/agent_{config_type}.yaml")
        if old_path.exists():
            with open(old_path, "r") as f:
                return yaml.safe_load(f)

        return {}


# 单例
config_compat = ConfigCompat()
