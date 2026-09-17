#!/usr/bin/env python3
"""Smart Config - Smart Config 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from pathlib import Path

from core.lib.unified_config import unified_config


class SmartConfig:
    """智能配置类 - 提供全局配置访问"""

    # 项目根目录
    ROOT = str(Path(__file__).parent.parent.parent.absolute())

    # 服务主机（默认 localhost，可从配置读取）
    HOST = "localhost"

    @classmethod
    def get(cls, path: str = None, default=None):
        """获取配置值"""
        if path is None:
            return unified_config.get("smart_config", {})
        return unified_config.get(f"smart_config.{path}", default)

    @classmethod
    def get_port(cls, service: str, default: int = None) -> int:
        """获取服务端口"""
        ports = unified_config.get("services", {})
        service_config = ports.get(service, {})
        return service_config.get("port", default or 8080)


# 全局单例
smart_config = SmartConfig()
