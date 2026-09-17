"""配置引擎 - 业务配置驱动，可热重载，可写"""

import time
from pathlib import Path
from typing import Dict, Tuple

import yaml

from engine.semantic.engines.base import BaseEngine


class ConfigEngine(BaseEngine):
    """配置引擎 - 从 keywords.yaml 读取"""

    def __init__(self):
        self._name = "config"
        self._priority = 3
        self._config_path = Path("config/keywords.yaml")
        self._config = None
        self._mtime = 0
        self._load()

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> int:
        return self._priority

    def _load(self):
        if not self._config_path.exists():
            self._config = {"intents": {}}
            return
        mtime = self._config_path.stat().st_mtime
        if self._config and mtime == self._mtime:
            return
        with open(self._config_path) as f:
            self._config = yaml.safe_load(f)
            self._mtime = mtime

    def understand(self, text: str) -> Tuple[str, float, Dict]:
        self._load()
        intents = self._config.get("intents", {})

        for intent, config in intents.items():
            for keyword in config.get("keywords", []):
                if keyword in text:
                    conf = min(len(keyword) / 10, 0.8)
                    return intent, conf, {"matched": keyword, "source": "config"}

        return "unknown", 0.0, {"source": "config"}

    def add_keyword(self, intent: str, keyword: str) -> Dict:
        """动态添加关键词（可写）"""
        self._load()
        if intent not in self._config.get("intents", {}):
            self._config["intents"][intent] = {"name": intent, "keywords": []}

        if keyword not in self._config["intents"][intent]["keywords"]:
            self._config["intents"][intent]["keywords"].append(keyword)
            self._save()
            return {"success": True, "added": keyword}
        return {"success": False, "reason": "already exists"}

    def _save(self):
        with open(self._config_path, "w") as f:
            yaml.dump(self._config, f, allow_unicode=True)

    def reload(self):
        self._mtime = 0
        self._load()

    def get_capabilities(self) -> Dict:
        return {
            "name": self.name,
            "priority": self.priority,
            "data_source": "keywords.yaml",
            "hot_reload": True,
            "writable": True,
        }


config_engine = ConfigEngine()
