#!/usr/bin/env python3
"""Config Version - Config Version 模块

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

"""配置版本管理 - 支持回滚"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ConfigVersionManager:
    """配置版本管理器"""

    def __init__(self):
        self.version_dir = Path(f"{get_data_root()}/config_versions")
        self.version_dir.mkdir(parents=True, exist_ok=True)

    def _get_config_hash(self, config: Dict) -> str:
        """生成配置哈希"""
        import hashlib

        content = json.dumps(config, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()[:8]

    def save_version(
        self, config_name: str, config: Dict, user: str = "system"
    ) -> Dict:
        """保存配置版本"""
        version_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_path = self.version_dir / config_name / version_id
        version_path.mkdir(parents=True, exist_ok=True)

        # 保存配置
        with open(version_path / "config.json", "w") as f:
            json.dump(config, f, indent=2)

        # 保存元数据
        metadata = {
            "version_id": version_id,
            "config_name": config_name,
            "created_at": datetime.now().isoformat(),
            "user": user,
            "hash": self._get_config_hash(config),
            "previous_hash": self.get_latest_hash(config_name),
        }
        with open(version_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        # 清理旧版本（保留最近10个）
        self._cleanup_old_versions(config_name, keep=10)

        return metadata

    def get_latest_hash(self, config_name: str) -> Optional[str]:
        """获取最新版本的哈希"""
        config_dir = self.version_dir / config_name
        if not config_dir.exists():
            return None

        versions = sorted([d for d in config_dir.iterdir() if d.is_dir()])
        if not versions:
            return None

        with open(versions[-1] / "metadata.json", "r") as f:
            metadata = json.load(f)
        return metadata.get("hash")

    def list_versions(self, config_name: str) -> List[Dict]:
        """列出所有版本"""
        config_dir = self.version_dir / config_name
        if not config_dir.exists():
            return []

        versions = []
        for v in sorted(config_dir.iterdir(), reverse=True):
            if v.is_dir():
                metadata_file = v / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)
                        versions.append(metadata)
        return versions

    def get_version(self, config_name: str, version_id: str) -> Optional[Dict]:
        """获取指定版本的配置"""
        version_path = self.version_dir / config_name / version_id
        if not version_path.exists():
            return None

        with open(version_path / "config.json", "r") as f:
            return json.load(f)

    def rollback(self, config_name: str, version_id: str) -> bool:
        """回滚到指定版本"""
        config = self.get_version(config_name, version_id)
        if not config:
            return False

        # 这里需要根据配置类型写入对应的配置文件
        # 简化版：只返回配置内容
        return {"success": True, "config": config}

    def _cleanup_old_versions(self, config_name: str, keep: int = 10):
        """清理旧版本"""
        config_dir = self.version_dir / config_name
        if not config_dir.exists():
            return

        versions = sorted([d for d in config_dir.iterdir() if d.is_dir()])
        for old in versions[:-keep]:
            shutil.rmtree(old)
            print(f"🗑️ 清理旧版本: {old.name}")


config_version_manager = ConfigVersionManager()


def register_version_routes(app):
    """注册版本管理路由"""

    @app.route("/api/config/versions/<config_name>", methods=["GET"])
    def list_config_versions(config_name):
        from flask import jsonify

        versions = config_version_manager.list_versions(config_name)
        return jsonify({"versions": versions, "count": len(versions)})

    @app.route("/api/config/versions/<config_name>/<version_id>", methods=["GET"])
    def get_config_version(config_name, version_id):
        from flask import jsonify

        config = config_version_manager.get_version(config_name, version_id)
        if config:
            return jsonify({"success": True, "config": config})
        return jsonify({"success": False, "error": "版本不存在"}), 404

    @app.route(
        "/api/config/versions/<config_name>/rollback/<version_id>", methods=["POST"]
    )
    def rollback_config(config_name, version_id):
        from flask import jsonify

        result = config_version_manager.rollback(config_name, version_id)
        if result:
            return jsonify({"success": True, "message": f"已回滚到版本 {version_id}"})
        return jsonify({"success": False, "error": "回滚失败"}), 400

    print("✅ 配置版本管理 API 已注册")


# 保存当前配置版本的回调
def save_current_config_version(config_name: str, config: Dict, user: str = "system"):
    """保存当前配置版本"""
    return config_version_manager.save_version(config_name, config, user)


# DEPRECATED: 请使用 unified_config 代替
