#!/usr/bin/env python3
"""Config Validator - Config Validator 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from pathlib import Path
from typing import Any, Dict, List

import yaml


class ConfigValidator:
    """配置校验 - 及早发现错误"""

    # 配置 schema 定义
    SCHEMAS = {
        "preferences": {
            "required": ["extraction_patterns", "query_patterns"],
            "types": {"extraction_patterns": list, "query_patterns": list},
        },
        "agent": {
            "required": ["name", "version"],
            "types": {"name": str, "version": str, "enabled": bool},
        },
    }

    def validate(self, config_name: str, config_path: Path) -> List[str]:
        """校验配置文件"""
        errors = []

        if not config_path.exists():
            return [f"配置文件不存在: {config_path}"]

        try:
            with open(config_path, "r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return [f"YAML解析错误: {e}"]

        schema = self.SCHEMAS.get(config_name)
        if not schema:
            return []

        # 检查必需字段
        for required in schema.get("required", []):
            if required not in data:
                errors.append(f"缺少必需字段: {required}")

        # 检查类型
        for field, expected_type in schema.get("types", {}).items():
            if field in data and not isinstance(data[field], expected_type):
                errors.append(f"字段 {field} 类型错误，期望 {expected_type}")

        return errors


config_validator = ConfigValidator()
