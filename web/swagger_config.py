#!/usr/bin/env python3
"""Swagger Config - Swagger Config 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from lib.smart_config import smart_config

"""Swagger API 文档配置"""
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "ClawsJoy API",
        "description": "ClawsJoy 智能系统 API 文档",
        "version": "3.0.0",
        "contact": {"name": "ClawsJoy", "email": "support@clawsjoy.local"},
    },
    "host": f"localhost:{smart_config.get_port("gateway")}",
    "basePath": "/",
    "schemes": ["http"],
    "tags": [
        {"name": "health", "description": "健康检查"},
        {"name": "skills", "description": "技能管理"},
        {"name": "agent", "description": "大脑调度"},
        {"name": "registry", "description": "注册中心"},
    ],
}
