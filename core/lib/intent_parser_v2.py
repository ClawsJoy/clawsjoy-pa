"""配置驱动的意图解析器 - 从统一配置文件读取"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from core.lib.unified_config import unified_config


class IntentParserV2:
    """配置驱动的意图解析器"""

    _instance = None
    _config = None
    _config_file = Path("config/keywords.yaml")  # 改为统一配置
    _last_modified = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载配置文件"""
        if self._config_file.exists():
            with open(self._config_file, "r") as f:
                self._config = yaml.safe_load(f)
                self._last_modified = self._config_file.stat().st_mtime
        else:
            # 兼容旧配置
            old_file = Path("config/intents.yaml")
            if old_file.exists():
                with open(old_file, "r") as f:
                    self._config = yaml.safe_load(f)
                    print("⚠️ 使用旧配置文件，建议迁移到 config/keywords.yaml")
            else:
                self._config = {"intents": {}}

    def _check_reload(self):
        """检查是否需要热重载"""
        if self._config_file.exists():
            current_mtime = self._config_file.stat().st_mtime
            if current_mtime > self._last_modified:
                self._load_config()
                print("🔄 意图配置已热重载")

    def parse(self, text: str) -> Dict:
        """解析意图"""
        self._check_reload()

        if not text:
            return {"intent": "unknown", "confidence": 0, "skills": []}

        text_lower = text.lower()
        best_intent = None
        best_score = 0
        matched_keywords = []

        intents = self._config.get("intents", {})

        for intent_name, intent_config in intents.items():
            keywords = intent_config.get("keywords", [])
            score = 0
            matched = []

            for keyword in keywords:
                if keyword in text_lower:
                    # 加权匹配
                    try:
                        weight = unified_config.get(
                            f"keywords.weighted_keywords.{intent_name}.{keyword}", 1
                        )
                    except Exception as e:
                        weight = 1
                    score += weight
                    matched.append(keyword)
                # 正则匹配
                elif keyword.startswith(".*") or keyword.endswith(".*"):
                    if re.search(keyword, text_lower):
                        # 正则匹配权重更高
                        try:
                            weight = unified_config.get(
                                f"keywords.weighted_keywords.{intent_name}.{keyword}", 2
                            )
                        except Exception as e:
                            weight = 2
                        score += weight
                        matched.append(keyword)

            if score > best_score:
                best_score = score
                best_intent = intent_name
                matched_keywords = matched

        if best_intent and best_score > 0:
            intent_config = intents.get(best_intent, {})
            return {
                "intent": best_intent,
                "name": intent_config.get("name", best_intent),
                "confidence": min(best_score / 5, 1.0),
                "skills": intent_config.get("skills", []),
                "priority": intent_config.get("priority", 10),
                "response_template": intent_config.get("response_template"),
                "matched_keywords": matched_keywords,
            }

        return {
            "intent": "unknown",
            "confidence": 0,
            "skills": ["chat_agent"],
            "matched_keywords": [],
        }

    def get_extractors(self) -> Dict:
        """获取实体提取器配置"""
        self._check_reload()
        return self._config.get("extractors", {})

    def get_all_intents(self) -> Dict:
        """获取所有意图配置"""
        self._check_reload()
        return self._config.get("intents", {})

    def reload(self):
        """手动重载配置"""
        self._load_config()
        print("✅ 意图配置已重载")


# 全局实例
intent_parser = IntentParserV2()
