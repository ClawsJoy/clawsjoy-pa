#!/usr/bin/env python3
"""Permission Decorator - Permission Decorator 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from functools import wraps
from pathlib import Path

import yaml
from flask import g, jsonify, request


def load_permissions():
    perm_file = Path("config/permissions.yaml")
    if perm_file.exists():
        with open(perm_file, "r") as f:
            return yaml.safe_load(f)
    return {}


def require_permission(level: int = 2):
    """权限装饰器"""

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_role = request.headers.get("X-User-Role", "user")
            permissions = load_permissions()
            levels = permissions.get("levels", {})

            allowed = False
            for lvl, config in levels.items():
                if int(lvl[-1]) == level and user_role in config.get("roles", []):
                    allowed = True
                    break

            if not allowed and level == 2:
                allowed = user_role in [
                    "user",
                    "developer",
                    "tenant_admin",
                    "system_admin",
                ]

            if not allowed:
                return (
                    jsonify({"success": False, "error": f"需要 level {level} 权限"}),
                    403,
                )

            return f(*args, **kwargs)

        return decorated

    return decorator
