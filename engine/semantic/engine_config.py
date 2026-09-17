"""引擎配置加载器 - 从统一配置读取"""

from typing import Any, Dict

from core.lib.unified_config import unified_config


class EngineConfig:
    """引擎配置管理"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_llm_config(self) -> Dict:
        """获取 LLM 引擎配置"""
        return unified_config.get(
            "keywords.engine_config.llm",
            {
                "enabled": True,
                "model": "qwen2.5:3b",
                "priority": 1,
                "timeout": 60,
                "confidence_threshold": 0.7,
            },
        )

    def get_vector_config(self) -> Dict:
        """获取向量引擎配置"""
        return unified_config.get(
            "keywords.engine_config.vector",
            {"enabled": True, "priority": 2, "confidence_threshold": 0.5},
        )

    def get_config_engine_config(self) -> Dict:
        """获取配置引擎配置"""
        return unified_config.get(
            "keywords.engine_config.config",
            {"enabled": True, "priority": 3, "confidence_threshold": 0.3},
        )

    def get_rule_config(self) -> Dict:
        """获取规则引擎配置"""
        return unified_config.get(
            "keywords.engine_config.rule",
            {"enabled": True, "priority": 4, "confidence_threshold": 0.2},
        )

    def get_priority_order(self) -> list:
        """获取引擎优先级顺序"""
        engines = []
        for name in ["llm", "vector", "config", "rule"]:
            config = unified_config.get(f"keywords.engine_config.{name}", {})
            if config.get("enabled", True):
                engines.append(
                    {
                        "name": name,
                        "priority": config.get("priority", 99),
                        "confidence_threshold": config.get("confidence_threshold", 0.3),
                    }
                )
        return sorted(engines, key=lambda x: x["priority"])


engine_config = EngineConfig()
