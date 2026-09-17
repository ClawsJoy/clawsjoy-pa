"""统一配置加载器 - 支持热重载"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


class ConfigLoader:
    """统一配置加载器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 支持多种配置路径
        self.config_paths = [
            Path("config/keywords.yaml"),  # 统一配置
            Path("config/engines/keywords.yaml"),
        ]
        self.config_dir = Path("config/engines")
        self.main_config = None
        self.keywords_config = None
        self.engine_configs = {}
        self._load_all()

    def _load_all(self):
        """加载所有配置"""
        # 优先加载统一配置
        for config_path in self.config_paths:
            if config_path.exists():
                with open(config_path, "r") as f:
                    self.keywords_config = yaml.safe_load(f)
                    print(f"✅ 从 {config_path} 加载配置")
                    break

        # 加载引擎配置
        if self.config_dir.exists():
            main_file = self.config_dir / "engines.yaml"
            if main_file.exists():
                with open(main_file, "r") as f:
                    self.main_config = yaml.safe_load(f)

            for yaml_file in self.config_dir.glob("*.yaml"):
                if yaml_file.name not in ["engines.yaml", "keywords.yaml"]:
                    with open(yaml_file, "r") as f:
                        self.engine_configs[yaml_file.stem] = yaml.safe_load(f)

    def reload(self):
        """热重载配置"""
        self._load_all()
        print("🔄 配置已热重载")

    def get_keywords(self, category: str, name: str = None) -> list:
        """获取关键词"""
        if not self.keywords_config:
            return []

        if category == "intent":
            intents = self.keywords_config.get("intents", {})
            if name:
                return intents.get(name, {}).get("keywords", [])
            return intents

        elif category == "skill":
            skills = self.keywords_config.get("skills", {})
            if name:
                return skills.get(name, {}).get("keywords", [])
            return skills

        elif category == "agent":
            agents = self.keywords_config.get("agent_mapping", {})
            if name:
                return agents.get(name, {}).get("keywords", [])
            return agents

        return []

    def get_intent_config(self, intent_name: str = None) -> Dict:
        """获取意图配置"""
        intents = self.keywords_config.get("intents", {})
        if intent_name:
            return intents.get(intent_name, {})
        return intents

    def get_extractors(self) -> Dict:
        """获取实体提取器配置"""
        return self.keywords_config.get("extractors", {})

    def get_agent_mapping(self) -> Dict:
        """获取 Agent 映射"""
        return self.keywords_config.get("agent_mapping", {})

    def get_engine_config(self, engine_name: str) -> Dict:
        """获取引擎配置"""
        return self.engine_configs.get(engine_name, {})


config_loader = ConfigLoader()
