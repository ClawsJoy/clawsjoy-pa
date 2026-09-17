"""向量化引擎核心"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from engine.embedding.local_embedding import local_embedding


class EmbeddingEngine:
    """向量化引擎"""

    def __init__(self):
        self._engine = local_embedding

    def process(self, input_data: Any = None, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, str):
            return self._process_string(input_data, **kwargs)
        return self._process_dict(input_data, **kwargs)

    def _process_string(self, text: str, **kwargs) -> Dict:
        """处理字符串"""
        return {"text": text, "similarity": self.similarity(text, text)}

    def _process_dict(self, data: dict, **kwargs) -> Dict:
        """处理字典"""
        return {"data": data, "status": "processed"}

    def similarity(self, text1: str, text2: str) -> float:
        return self._engine.similarity(text1, text2)

    def encode(self, texts: List[str]) -> List[List[float]]:
        return self._engine.encode(texts)

    def get_stats(self) -> Dict:
        return self._engine.get_stats()

    def reload(self) -> Dict:
        return {"success": True, "message": "Embedding engine reloaded"}

    def health_check(self) -> Dict:
        return {"name": "embedding_engine", "status": "healthy"}


embedding_engine = EmbeddingEngine()
