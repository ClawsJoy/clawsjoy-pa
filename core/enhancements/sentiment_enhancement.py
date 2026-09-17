"""情感分析增强 - 可选插件"""

class SentimentEnhancement:
    """情感分析增强"""
    
    def __init__(self):
        self.enabled = False
        try:
            from engine.emotion.emotion_engine import EmotionEngine
            self.engine = EmotionEngine()
            self.enabled = True
            print("✅ 情感分析增强已启用")
        except Exception as e:
            print(f"⚠️ 情感分析增强不可用: {e}")
    
    def analyze(self, text: str):
        if not self.enabled:
            return {"sentiment": "neutral", "score": 0}
        return self.engine.analyze(text)

sentiment_enhancement = SentimentEnhancement()
