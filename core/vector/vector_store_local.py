#!/usr/bin/env python3
"""Vector Store Local - Vector Store Local 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from core.local_embedding import embedding_model


class VectorStoreLocal:
    """本地向量存储"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.base_path = Path(
            f"{config_helper.get_data_root()}/users/{user_id}/vectors"
        )
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.documents = []
        self.embeddings = []
        self._load()

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

        # 使用本地 embedding
        embedding = embedding_model.encode(text)
        self.embeddings.append(np.array(embedding))

        # 限制数量
        if len(self.documents) > 500:
            self.documents = self.documents[-500:]
            self.embeddings = self.embeddings[-500:]

        self._save()

    def search(self, query: str, limit: int = 3) -> List[Dict]:
        """语义搜索"""
        if not self.embeddings:
            return []

        query_vec = embedding_model.encode(query)

        # 计算相似度
        similarities = []
        for i, doc_vec in enumerate(self.embeddings):
            # 确保维度一致
            min_len = min(len(query_vec), len(doc_vec))
            qv = query_vec[:min_len]
            dv = doc_vec[:min_len]

            norm_q = np.linalg.norm(qv)
            norm_d = np.linalg.norm(dv)
            if norm_q > 0 and norm_d > 0:
                sim = np.dot(qv, dv) / (norm_q * norm_d)
            else:
                sim = 0
            similarities.append((sim, i))

        similarities.sort(key=lambda x: x[0], reverse=True)

        results = []
        for sim, idx in similarities[:limit]:
            if sim > 0.3:
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


vector_store = VectorStoreLocal
