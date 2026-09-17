#!/usr/bin/env python3
"""Vector Store - Vector Store 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np


class VectorStore:
    """向量存储"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.base_path = Path(
            f"{config_helper.get_data_root()}/users/{user_id}/vectors"
        )
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.documents = []
        self.embeddings = []
        self._load()
        self._init_model()

    def _init_model(self):
        """初始化 embedding 模型"""
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            print("   ✅ embedding 模型已加载")
        except Exception as e:
            print("   ⚠️ sentence-transformers 未安装，使用简化版")
            self.model = None

    def _load(self):
        file_path = self.base_path / "store.json"
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    self.documents = data.get("documents", [])
                    self.embeddings = [np.array(e) for e in data.get("embeddings", [])]
            except Exception as e:
                pass

    def _save(self):
        with open(self.base_path / "store.json", "w") as f:
            json.dump(
                {
                    "documents": self.documents,
                    "embeddings": [e.tolist() for e in self.embeddings],
                },
                f,
                indent=2,
            )

    def add(self, text: str, metadata: Dict = None):
        """添加文档"""
        import time
        import uuid

        doc_id = str(uuid.uuid4())[:8]
        self.documents.append(
            {
                "id": doc_id,
                "text": text,
                "metadata": metadata or {},
                "timestamp": time.time(),
            }
        )

        # 计算 embedding
        if self.model:
            embedding = self.model.encode(text)
        else:
            # 简化版：使用 TF-IDF 风格
            embedding = self._simple_embedding(text)

        self.embeddings.append(np.array(embedding))

        # 限制数量
        if len(self.documents) > 500:
            self.documents = self.documents[-500:]
            self.embeddings = self.embeddings[-500:]

        self._save()

    def _simple_embedding(self, text: str) -> List[float]:
        """简化版 embedding"""
        import hashlib

        words = text.lower().split()[:30]
        vec = []
        for w in words:
            h = hashlib.md5(w.encode()).hexdigest()[:8]
            vec.append(int(h, 16) % 100 / 100)
        while len(vec) < 30:
            vec.append(0.0)
        return vec

    def search(self, query: str, limit: int = 3) -> List[Dict]:
        """语义搜索"""
        if not self.embeddings:
            return []

        # 计算查询向量
        if self.model:
            query_vec = self.model.encode(query)
        else:
            query_vec = self._simple_embedding(query)

        # 计算相似度
        similarities = []
        for i, doc_vec in enumerate(self.embeddings):
            sim = np.dot(query_vec, doc_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(doc_vec) + 1e-8
            )
            similarities.append((sim, i))

        similarities.sort(key=lambda x: x[0], reverse=True)

        results = []
        for sim, idx in similarities[:limit]:
            if sim > 0.3:  # 相似度阈值
                results.append(
                    {
                        "text": self.documents[idx]["text"],
                        "score": float(sim),
                        "metadata": self.documents[idx]["metadata"],
                    }
                )

        return results

    def get_stats(self) -> Dict:
        return {"total": len(self.documents)}


vector_store = VectorStore
