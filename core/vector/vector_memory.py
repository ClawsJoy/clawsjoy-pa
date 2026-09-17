#!/usr/bin/env python3
"""Vector Memory - Vector Memory 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Dict, List


class VectorMemory:
    """向量记忆系统"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.base_path = Path(
            f"{config_helper.get_data_root()}/users/{user_id}/vector_memory"
        )
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.memories = self._load()

    def _load(self) -> List[Dict]:
        file_path = self.base_path / "memories.json"
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                pass
        return []

    def _save(self):
        with open(self.base_path / "memories.json", "w") as f:
            json.dump(self.memories, f, indent=2)

    def _tokenize(self, text: str) -> List[str]:
        import re

        return re.findall(r"[\u4e00-\u9fa5a-zA-Z]+", text.lower())

    def _vectorize(self, text: str) -> Dict[str, float]:
        words = self._tokenize(text)
        counter = Counter(words)
        total = len(words)
        return {w: c / total for w, c in counter.items()}

    def _similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        words = set(vec1.keys()) | set(vec2.keys())
        dot = sum(vec1.get(w, 0) * vec2.get(w, 0) for w in words)
        norm1 = math.sqrt(sum(v * v for v in vec1.values()))
        norm2 = math.sqrt(sum(v * v for v in vec2.values()))
        return dot / (norm1 * norm2 + 1e-8)

    def add(self, text: str, metadata: Dict = None):
        """添加记忆"""
        memory_id = hashlib.md5(f"{text}{len(self.memories)}".encode()).hexdigest()[:8]
        self.memories.append(
            {
                "id": memory_id,
                "text": text,
                "vector": self._vectorize(text),
                "metadata": metadata or {},
                "timestamp": time.time(),
            }
        )
        if len(self.memories) > 500:
            self.memories = self.memories[-500:]
        self._save()

    def search(self, query: str, limit: int = 3) -> List[Dict]:
        """语义搜索"""
        query_vec = self._vectorize(query)
        results = []
        for mem in self.memories:
            score = self._similarity(query_vec, mem["vector"])
            results.append((score, mem))

        results.sort(key=lambda x: x[0], reverse=True)
        return [
            {"text": r[1]["text"], "score": round(r[0], 3)}
            for r in results[:limit]
            if r[0] > 0.1
        ]


import time
