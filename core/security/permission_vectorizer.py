#!/usr/bin/env python3
"""Permission Vectorizer - Permission Vectorizer 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from pathlib import Path

import yaml

from core.lib.unified_config import unified_config
from core.tenant.tenant_vector_index import tenant_index_manager


class PermissionVectorizer:
    """权限向量化 - 配置驱动权限检查"""

    def __init__(self):
        self._rules = {}
        self._load_permission_rules()

    def _load_permission_rules(self):
        """加载权限规则配置"""
        config_file = Path("config/permissions.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                self._rules = yaml.safe_load(f)
        else:
            # 默认权限规则
            self._rules = {
                "roles": {
                    "admin": ["*"],
                    "user": ["skill.execute", "knowledge.search", "memory.*"],
                    "guest": ["skill.list", "knowledge.search"],
                },
                "api_permissions": {
                    "/api/admin/*": ["admin"],
                    "/api/skills/execute": ["user", "admin"],
                    "/api/marketplace/*": ["admin"],
                },
            }

    def check_permission(self, user_role: str, resource: str, action: str = "read"):
        """检查权限 - 配置驱动"""
        # 获取角色权限
        role_perms = self._rules.get("roles", {}).get(user_role, [])

        # 通配符匹配
        for perm in role_perms:
            if perm == "*":
                return True
            if perm.endswith(".*"):
                prefix = perm[:-2]
                if resource.startswith(prefix):
                    return True
            if perm == f"{resource}.{action}":
                return True

        return False

    def get_allowed_apis(self, user_role: str):
        """获取用户有权限的 API 列表"""
        api_perms = self._rules.get("api_permissions", {})
        allowed = []

        for api_path, roles in api_perms.items():
            if user_role in roles:
                allowed.append(api_path)

        return allowed


permission_vectorizer = PermissionVectorizer()
