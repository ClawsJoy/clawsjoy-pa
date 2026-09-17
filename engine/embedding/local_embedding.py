"""本地向量化引擎 - 使用系统向量中心"""

import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engine.lib.logger import engine_logger


class LocalEmbeddingEngine:
    """本地向量化引擎"""

    def __init__(self):
        self.vector_center = None
        self._init_vector_center()
        engine_logger.get().info("🔢 本地向量化引擎已初始化")

    def _init_vector_center(self):
        try:
            from core.lib.vector_knowledge_center import vector_knowledge_center

            self.vector_center = vector_knowledge_center
            engine_logger.get().info("   ✅ 已连接向量知识中心")
        except Exception as e:
            engine_logger.get().warning(f"   ⚠️ 向量中心连接失败: {e}")

    def encode(self, texts: List[str]) -> List[List[float]]:
        """文本向量化"""
        if self.vector_center and hasattr(self.vector_center, "_get_embedding"):
            embeddings = []
            for text in texts:
                try:
                    emb = self.vector_center._get_embedding(text)
                    if emb:
                        embeddings.append(emb)
                    else:
                        embeddings.append(self._hash_embedding(text))
                except Exception as e:
                    embeddings.append(self._hash_embedding(text))
            return embeddings
        return [self._hash_embedding(text) for text in texts]

    def _hash_embedding(self, text: str, dim: int = 384) -> List[float]:
        """哈希向量降级方案"""
        hash_bytes = hashlib.md5(text.encode()).digest()
        return [hash_bytes[i % 16] / 255.0 for i in range(dim)]

    def similarity(self, text1: str, text2: str) -> float:
        """计算相似度"""
        emb1 = self.encode([text1])[0]
        emb2 = self.encode([text2])[0]
        dot = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = sum(a * a for a in emb1) ** 0.5
        norm2 = sum(b * b for b in emb2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def search(self, query: str, candidates: List[str], top_k: int = 5) -> List[tuple]:
        """搜索相似文本"""
        query_emb = self.encode([query])[0]
        similarities = []
        for candidate in candidates:
            cand_emb = self.encode([candidate])[0]
            sim = self._cosine_similarity(query_emb, cand_emb)
            similarities.append((candidate, sim))
        similarities.sort(key=lambda x: -x[1])
        return similarities[:top_k]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0

    def get_stats(self) -> Dict:
        return {
            "status": "active",
            "using_vector_center": self.vector_center is not None,
        }


local_embedding = LocalEmbeddingEngine()
