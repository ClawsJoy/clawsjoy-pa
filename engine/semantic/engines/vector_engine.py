"""向量引擎 - 只与向量库交互，支持新知识向量化"""

import hashlib
import time
from typing import Dict, Optional, Tuple

from engine.semantic.engines.base import BaseEngine


class VectorEngine(BaseEngine):
    """
    向量引擎 - 语义理解

    设计哲学:
    1. 只与向量库交互，不关心关键词
    2. 新知识可动态向量化入库
    3. 优先级2，介于LLM和配置之间
    """

    def __init__(self):
        self._name = "vector"
        self._priority = 2
        self._collection = None
        self._init_collection()

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> int:
        return self._priority

    def _init_collection(self):
        """初始化向量集合"""
        try:
            from core.lib.vector_knowledge_center import vector_knowledge_center

            self._collection = vector_knowledge_center._get_or_create_collection(
                "intent_vectors"
            )
            print(f"✅ 向量引擎已初始化")
        except Exception as e:
            print(f"⚠️ 向量引擎初始化失败: {e}")

    def understand(self, text: str) -> Tuple[str, float, Dict]:
        """向量理解 - 向量检索"""
        if not self._collection:
            return "unknown", 0.0, {"error": "vector collection not available"}

        try:
            results = self._collection.query(query_texts=[text], n_results=1)

            if results and results.get("distances") and results["distances"][0]:
                distance = results["distances"][0][0]
                confidence = 1 - min(distance, 1.0)

                if results.get("metadatas") and results["metadatas"][0]:
                    intent = results["metadatas"][0][0].get("intent", "unknown")
                    return (
                        intent,
                        confidence,
                        {"distance": distance, "source": "vector"},
                    )
        except Exception as e:
            pass

        return "unknown", 0.0, {"source": "vector"}

    def learn(self, text: str, intent: str, confidence: float) -> Dict:
        """学习新知识 - 将新文本向量化入库"""
        if confidence < 0.7:
            return {"success": False, "reason": "confidence too low"}

        if not self._collection:
            return {"success": False, "reason": "collection not available"}

        try:
            doc_id = hashlib.md5(f"{intent}_{text}_{time.time()}".encode()).hexdigest()[
                :16
            ]
            self._collection.add(
                ids=[doc_id],
                documents=[text],
                metadatas=[
                    {"intent": intent, "source": "learned", "confidence": confidence}
                ],
            )
            return {"success": True, "id": doc_id, "intent": intent}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sync_from_config(self) -> Dict:
        """从配置同步：将 keywords.yaml 中的关键词向量化"""
        try:
            from core.lib.unified_config import unified_config

            intents = unified_config.get("keywords.intents", {})

            count = 0
            for intent_name, intent_config in intents.items():
                for keyword in intent_config.get("keywords", []):
                    doc_id = hashlib.md5(
                        f"config_{intent_name}_{keyword}".encode()
                    ).hexdigest()[:16]
                    self._collection.upsert(
                        ids=[doc_id],
                        documents=[keyword],
                        metadatas=[{"intent": intent_name, "source": "config"}],
                    )
                    count += 1

            return {"success": True, "synced": count}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def is_available(self) -> bool:
        return self._collection is not None

    def get_stats(self) -> Dict:
        return {
            "name": self.name,
            "priority": self.priority,
            "available": self.is_available(),
            "type": "semantic_vector",
        }

    def get_capabilities(self) -> Dict:
        return self.get_stats()


vector_engine = VectorEngine()
