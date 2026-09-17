#!/usr/bin/env python3
"""Route Vectorizer - Route Vectorizer 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import hashlib

from core.lib.route_handlers import HANDLERS
from core.lib.route_registry import route_registry
from core.tenant.tenant_vector_index import tenant_index_manager


class RouteVectorizer:
    """路由向量化器 - 为动态路由提供语义匹配"""

    def __init__(self):
        self._initialized = False

    def init_tenant_routes(self, tenant_id: str = "default"):
        """初始化租户路由向量索引"""
        if self._initialized:
            return

        # 获取所有启用的路由
        routes = route_registry.get_all_enabled()

        index = tenant_index_manager.get_index(tenant_id)

        for route in routes:
            path = route.get("path", "")
            method = route.get("method", "GET")
            handler = route.get("handler", "")
            description = route.get("description", "")

            if path and handler:
                index.index_route(path, method, handler, description)

        print(f"   📍 已向量化 {len(routes)} 条路由")
        self._initialized = True
        return len(routes)

    def match_route(self, tenant_id: str, query: str, n: int = 3):
        """根据用户意图匹配最相关路由"""
        index = tenant_index_manager.get_index(tenant_id)
        return index.search_route(query, n)

    def get_stats(self, tenant_id: str = "default"):
        """获取路由向量统计"""
        index = tenant_index_manager.get_index(tenant_id)
        return index.get_stats()


route_vectorizer = RouteVectorizer()
