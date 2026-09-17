#!/usr/bin/env python3
"""File Utils - File Utils 模块

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

"""文件处理工具"""
import os
import uuid
from datetime import datetime
from pathlib import Path


class FileUtils:
    @staticmethod
    def get_output_dir() -> Path:
        """获取输出目录"""
        output_dir = Path(f"{get_data_root()}/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    @staticmethod
    def generate_filename(prefix: str, extension: str = "mp4") -> str:
        """生成唯一文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{prefix}_{timestamp}_{unique_id}.{extension}"

    @staticmethod
    def save_output(content: bytes, filename: str) -> Path:
        """保存输出文件"""
        output_dir = FileUtils.get_output_dir()
        filepath = output_dir / filename
        with open(filepath, "wb") as f:
            f.write(content)
        return filepath

    @staticmethod
    def file_exists(filepath: str) -> bool:
        """检查文件是否存在"""
        return Path(filepath).exists()


file_utils = FileUtils()
