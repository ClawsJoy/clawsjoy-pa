"""向量引擎自动学习器"""

import time
from pathlib import Path
from typing import Dict, List

from core.lib.vector_knowledge_center import vector_knowledge_center


class VectorLearner:
    """向量引擎自动学习 - 从用户反馈中学习"""

    def __init__(self):
        self.learning_queue = []
        self.feedback_file = Path("data/vector_feedback.json")

    def record_learning(self, user_input: str, correct_intent: str, confidence: float):
        """记录学习样本"""
        if confidence < 0.7:
            return
        self.learning_queue.append(
            {"text": user_input, "intent": correct_intent, "timestamp": time.time()}
        )
        if len(self.learning_queue) >= 10:
            self.sync_to_vector()

    def sync_to_vector(self):
        """同步学习样本到向量库"""
        if not self.learning_queue:
            return
        collection = vector_knowledge_center._get_or_create_collection("skills")
        for item in self.learning_queue:
            collection.upsert(
                ids=[f"learned_{item['intent']}_{hash(item['text'])}"],
                documents=[item["text"]],
                metadatas=[{"name": item["intent"], "source": "learned"}],
            )
        print(f"📚 向量引擎学习了 {len(self.learning_queue)} 个新样本")
        self.learning_queue = []


vector_learner = VectorLearner()
