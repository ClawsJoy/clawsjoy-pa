#!/usr/bin/env python3
"""Config Driven Matcher - Config Driven Matcher 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tenant.tenant_vector_index import tenant_index_manager


class ConfigDrivenMatcher:
    """配置驱动的匹配器 - 单例模式"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.tenant_id = "default"
        self.index = tenant_index_manager.get_index(self.tenant_id)
        self._load_configs()
        self._init_watcher()

    def _init_watcher(self):
        """初始化配置监听"""
        try:
            from core.lib.config_watcher import config_watcher

            mapping_file = Path(__file__).parent.parent / "config/skill_mapping.yaml"
            config_watcher.register(str(mapping_file), self.reload_config)
        except Exception as e:
            print(f"⚠️ 配置监听启动失败: {e}")

    def _load_configs(self):
        """加载所有配置"""
        mapping_file = Path(__file__).parent.parent / "config/skill_mapping.yaml"
        if mapping_file.exists():
            with open(mapping_file, "r") as f:
                self.mapping_config = yaml.safe_load(f)
        else:
            self.mapping_config = {"mappings": {}, "category_mappings": {}}

    def reload_config(self):
        """热重载配置"""
        self._load_configs()
        print("✅ 技能匹配配置已热重载")
        return True

    def match(self, query: str, tenant_id: str = None) -> dict:
        """匹配技能"""
        mappings = self.mapping_config.get("mappings", {})

        # 精确匹配
        if query in mappings:
            return {
                "success": True,
                "query": query,
                "matched_skill": mappings[query],
                "similarity": 1.0,
                "match_type": "exact_mapping",
            }

        # 分类匹配
        category_mappings = self.mapping_config.get("category_mappings", {})
        for category, skill_name in category_mappings.items():
            if category in query or query in category:
                return {
                    "success": True,
                    "query": query,
                    "matched_skill": skill_name,
                    "similarity": 0.9,
                    "match_type": "category_mapping",
                }

        # 向量搜索
        results = self.index.search_skill(query, 5)
        if results:
            best = results[0]
            return {
                "success": True,
                "query": query,
                "matched_skill": best["name"],
                "similarity": round(best["similarity"], 3),
                "match_type": "vector_search",
            }

        return {
            "success": False,
            "query": query,
            "matched_skill": None,
            "similarity": 0,
            "match_type": "none",
        }


# 全局实例
matcher = ConfigDrivenMatcher()


if __name__ == "__main__":
    print("配置驱动匹配测试:")
    for q in ["计算", "加法", "翻译", "天气"]:
        result = matcher.match(q)
        print(f"  {q} -> {result['matched_skill']} ({result['match_type']})")
