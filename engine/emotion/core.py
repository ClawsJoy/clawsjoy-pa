"""情感计算引擎"""

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from engine.lib.logger import engine_logger


class EmotionEngine:
    """情感计算引擎"""

    EMOTION_LEXICON = {
        "positive": ["好", "棒", "喜欢", "开心", "高兴", "感谢", "谢谢", "不错", "赞"],
        "negative": ["坏", "差", "讨厌", "烦", "生气", "愤怒", "糟糕", "失望"],
        "satisfied": ["满意", "解决了", "好了", "可以了"],
    }

    def __init__(self):
        self.user_history = defaultdict(list)
        engine_logger.get().info("😊 情感计算引擎已初始化")

    def process(self, input_data: Any = None, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, str):
            return self.analyze(input_data, kwargs.get("user_id"))
        if isinstance(input_data, dict):
            return self.analyze(input_data.get("text", ""), input_data.get("user_id"))
        return self.analyze(str(input_data))

    def analyze(self, text: str, user_id: str = None) -> Dict:
        """分析文本情感"""
        scores = {emotion: 0 for emotion in self.EMOTION_LEXICON}
        for emotion, keywords in self.EMOTION_LEXICON.items():
            for kw in keywords:
                scores[emotion] += text.count(kw)

        dominant = max(scores.items(), key=lambda x: x[1])
        sentiment = (
            "positive"
            if scores["positive"] + scores["satisfied"] > scores["negative"]
            else "negative"
        )

        result = {
            "dominant_emotion": dominant[0] if dominant[1] > 0 else "neutral",
            "intensity": dominant[1],
            "sentiment": sentiment,
            "text": text[:50],
        }

        if user_id:
            self.user_history[user_id].append(result)
            if len(self.user_history[user_id]) > 50:
                self.user_history[user_id] = self.user_history[user_id][-50:]

        return result

    def get_user_trend(self, user_id: str) -> Dict:
        """获取用户情感趋势"""
        history = self.user_history.get(user_id, [])
        if not history:
            return {"status": "insufficient_data"}
        emotions = [h["dominant_emotion"] for h in history[-10:]]
        return {"emotion_distribution": dict(Counter(emotions)), "trend": "stable"}

    def get_stats(self) -> Dict:
        return {"total_users": len(self.user_history), "status": "active"}

    def reload(self) -> Dict:
        self.user_history.clear()
        return {"success": True, "message": "Emotion engine reloaded"}

    def health_check(self) -> Dict:
        return {"name": "emotion_engine", "status": "healthy"}


emotion_engine = EmotionEngine()
