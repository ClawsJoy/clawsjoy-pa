#!/usr/bin/env python3
"""Settings - Settings 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from lib.smart_config import smart_config

"""统一配置 - 消除硬编码"""
import os
from pathlib import Path


class Settings:
    """全局配置"""

    # 项目根目录（使用环境变量或自动检测）
    ROOT = Path(os.environ.get("CLAWSJOY_ROOT", Path(__file__).parent.parent.parent))

    # 服务端口
    GATEWAY_PORT = int(os.environ.get("CLAWSJOY_GATEWAY_PORT", 5002))
    FILE_PORT = int(os.environ.get("CLAWSJOY_FILE_PORT", 5003))
    MULTI_PORT = int(os.environ.get("CLAWSJOY_MULTI_PORT", 5006))

    # LLM 配置
    OLLAMA_ENDPOINT = os.environ.get("OLLAMA_HOST", "config_loader.get_ollama_url()")
    DEFAULT_MODEL = os.environ.get("CLAWSJOY_DEFAULT_MODEL", "qwen2.5:7b-instruct-q4_0-gpu")
    FAST_MODEL = os.environ.get("CLAWSJOY_FAST_MODEL", "qwen2.5:7b-instruct-q4_0-gpu")

    # 路径配置
    SKILLS_DIR = ROOT / "src/skills"
    ATOMIC_SKILLS_DIR = SKILLS_DIR / "atomic"
    WORKFLOW_DIR = SKILLS_DIR / "workflow"

    @classmethod
    def get_ollama_url(cls):
        return f"{cls.OLLAMA_ENDPOINT}/api/generate"


settings = Settings()
