#!/usr/bin/env python3
"""Intelligent Driver - Intelligent Driver 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import os
from typing import Any, Dict


class IntelligentDriver:
    """智能驱动类"""

    VERSION = "1.0.0"

    def __init__(self):
        self.config = {}

    def get_ollama_host(self) -> str:
        """获取 Ollama 主机"""
        return os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

    def get_port(self, service: str) -> int:
        """获取服务端口"""
        ports = {"ollama": 11434, "gateway": 5002, "multi_agent": 5006}
        return ports.get(service, 5002)


intelligent_driver = IntelligentDriver()
