#!/usr/bin/env python3
"""Tenant Manager - Tenant Manager 模块

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

"""租户管理器 - 配置驱动"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import yaml


class TenantManager:
    """租户管理器 - 配置驱动"""

    def __init__(self):
        self.config = self._load_config()
        self.base_path = Path(
            self.config.get("tenant", {}).get("base_path", f"{get_data_root()}/tenants")
        )
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> Dict:
        """加载租户配置"""
        config_file = Path("config/tenant.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                return unified_config.get("tenant_manager", {})
        return {"tenant": {"enabled": True, "base_path": f"{get_data_root()}/tenants"}}

    def get_tenant_config(self, tenant_id: str) -> Optional[Dict]:
        """获取租户配置"""
        tenants = self.config.get("tenants", [])
        for tenant in tenants:
            if tenant.get("id") == tenant_id:
                return tenant
        # 返回默认配置
        return self.config.get("default_tenant", {})

    def get_tenant_quota(self, tenant_id: str) -> Dict:
        """获取租户配额"""
        tenant_config = self.get_tenant_config(tenant_id)
        if tenant_config and "quota" in tenant_config:
            return tenant_config["quota"]
        return self.config.get("default_quota", {})

    def ensure_tenant_directory(self, tenant_id: str) -> Path:
        """确保租户目录存在"""
        tenant_dir = self.base_path / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        return tenant_dir

    def list_tenants(self) -> list:
        """列出所有租户"""
        tenants = self.config.get("tenants", [])
        # 同时扫描目录中的租户
        for d in self.base_path.iterdir():
            if d.is_dir() and d.name not in [t["id"] for t in tenants]:
                tenants.append(
                    {
                        "id": d.name,
                        "name": d.name,
                        "status": "active",
                        "created_at": datetime.fromtimestamp(
                            d.stat().st_ctime
                        ).isoformat(),
                    }
                )
        return tenants

    def create_tenant(self, tenant_id: str, name: str = None) -> Dict:
        """创建新租户"""
        rules = self.config.get("creation_rules", {})

        # 验证命名规则
        import re

        pattern = rules.get("naming_pattern", "^[a-z0-9_]{3,32}$")
        if not re.match(pattern, tenant_id):
            return {"success": False, "error": f"租户ID格式不符合规则: {pattern}"}

        # 检查是否已存在
        tenant_dir = self.base_path / tenant_id
        if tenant_dir.exists():
            return {"success": False, "error": "租户已存在"}

        # 创建目录
        tenant_dir.mkdir()

        # 创建租户配置文件
        tenant_config = {
            "id": tenant_id,
            "name": name or tenant_id,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "quota": self.config.get("default_quota", {}),
        }

        with open(tenant_dir / "config.json", "w") as f:
            json.dump(tenant_config, f, indent=2)

        return {"success": True, "tenant_id": tenant_id, "path": str(tenant_dir)}

    def delete_tenant(self, tenant_id: str) -> Dict:
        """删除租户"""
        import shutil

        tenant_dir = self.base_path / tenant_id
        if not tenant_dir.exists():
            return {"success": False, "error": "租户不存在"}

        shutil.rmtree(tenant_dir)
        return {"success": True, "message": f"租户 {tenant_id} 已删除"}


tenant_manager = TenantManager()
