#!/usr/bin/env python3
"""Prompt Version - Prompt Version 模块

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

"""提示词版本管理 - 追踪提示词变更"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml


class PromptVersion:
    """提示词版本管理器"""

    VERSIONS_DIR = Path(f"{get_data_root()}/prompt_versions")

    def __init__(self):
        self.VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self.current_file = Path("config/prompts.yaml")
        self._load_current()

    def _load_current(self):
        if self.current_file.exists():
            with open(self.current_file, "r") as f:
                self.current = unified_config.get("prompt_version", {})
        else:
            self.current = {}

    def save_version(self, tag: str, description: str = "") -> str:
        """保存当前版本"""
        version_id = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        version_file = self.VERSIONS_DIR / f"{version_id}.yaml"

        version_data = {
            "id": version_id,
            "tag": tag,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "prompts": self.current,
            "diff_from_previous": self._get_diff(),
        }

        with open(version_file, "w") as f:
            yaml.dump(version_data, f, allow_unicode=True)

        # 更新索引
        self._update_index(version_id, tag, description)

        return version_id

    def _get_diff(self) -> str:
        """获取与上一版本的差异"""
        versions = self.list_versions()
        if len(versions) < 2:
            return "首次版本"

        prev_file = self.VERSIONS_DIR / f"{versions[-2]['id']}.yaml"
        if prev_file.exists():
            with open(prev_file, "r") as f:
                prev = unified_config.get("prompt_version", {})
            # 简单比较
            if prev.get("prompts") != self.current:
                return "提示词有变更"
        return "无变更"

    def _update_index(self, version_id: str, tag: str, description: str):
        index_file = self.VERSIONS_DIR / "index.json"
        if index_file.exists():
            with open(index_file, "r") as f:
                index = json.load(f)
        else:
            index = {"versions": []}

        index["versions"].append(
            {
                "id": version_id,
                "tag": tag,
                "description": description,
                "timestamp": datetime.now().isoformat(),
            }
        )

        with open(index_file, "w") as f:
            json.dump(index, f, indent=2)

    def list_versions(self) -> List[Dict]:
        """列出所有版本"""
        index_file = self.VERSIONS_DIR / "index.json"
        if index_file.exists():
            with open(index_file, "r") as f:
                return json.load(f).get("versions", [])
        return []

    def rollback(self, version_id: str) -> bool:
        """回滚到指定版本"""
        version_file = self.VERSIONS_DIR / f"{version_id}.yaml"
        if not version_file.exists():
            return False

        with open(version_file, "r") as f:
            version_data = unified_config.get("prompt_version", {})

        # 备份当前
        self.save_version("pre_rollback", f"回滚前备份")

        # 恢复
        with open(self.current_file, "w") as f:
            yaml.dump(version_data.get("prompts", {}), f, allow_unicode=True)

        return True

    def compare(self, version_a: str, version_b: str) -> Dict:
        """比较两个版本"""
        file_a = self.VERSIONS_DIR / f"{version_a}.yaml"
        file_b = self.VERSIONS_DIR / f"{version_b}.yaml"

        if not file_a.exists() or not file_b.exists():
            return {"error": "版本不存在"}

        with open(file_a, "r") as f:
            data_a = unified_config.get("prompt_version", {})
        with open(file_b, "r") as f:
            data_b = unified_config.get("prompt_version", {})

        return {
            "version_a": version_a,
            "version_b": version_b,
            "timestamp_a": data_a.get("timestamp"),
            "timestamp_b": data_b.get("timestamp"),
            "dif": self._deep_diff(
                data_a.get("prompts", {}), data_b.get("prompts", {})
            ),
        }

    def _deep_diff(self, a: Dict, b: Dict) -> Dict:
        diff = {}
        all_keys = set(a.keys()) | set(b.keys())
        for key in all_keys:
            if a.get(key) != b.get(key):
                diff[key] = {"old": a.get(key), "new": b.get(key)}
        return diff


prompt_version = PromptVersion()
