"""意图关键词兜底配置加载器"""

import yaml
from pathlib import Path
from typing import Optional


class IntentFallback:
    _instance = None
    _keyword_to_intent = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        config_path = Path("config/intent_agent_map.yaml")
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                fallback = config.get("keyword_fallback", {})
                for intent, keywords in fallback.items():
                    for kw in keywords:
                        self._keyword_to_intent[kw] = intent
        else:
            # 默认关键词
            self._keyword_to_intent = {
                "写一篇": "write", "写一个": "write", "撰写": "write", "创作": "write", "文章": "write",
                "识别": "vision", "描述图片": "vision", "看图": "vision", "图像识别": "vision", "图片": "vision",
                "裁剪": "video", "转码": "video", "截图": "video", "视频": "video", "剪辑": "video",
            }

    def get_intent(self, text: str) -> Optional[str]:
        """根据关键词获取意图"""
        text_lower = text.lower()
        for kw, intent in self._keyword_to_intent.items():
            if kw in text_lower:
                return intent
        return None


intent_fallback = IntentFallback()
