"""技能矩阵引擎 v2"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from engine.skill_matrix.core import skill_matrix_engine


class SkillMatrixV2Engine:
    """技能矩阵引擎 v2 - 增强版"""

    def __init__(self):
        self._engine = skill_matrix_engine

    def process(self, input_data: Any = None, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, str):
            return self._process_string(input_data, **kwargs)
        return self._process_dict(input_data, **kwargs)

    def _process_string(self, text: str, **kwargs) -> Dict:
        """处理字符串 - 搜索技能"""
        top_k = kwargs.get("top_k", 5)
        return {"query": text, "results": self.search(text, top_k)}

    def _process_dict(self, data: dict, **kwargs) -> Dict:
        """处理字典"""
        query = data.get("query", "")
        top_k = data.get("top_k", 5)
        return self.search(query, top_k)

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        return self._engine.search(query, top_k)

    def search_skills(self, query: str, top_k: int = 5) -> List[Dict]:
        return self.search(query, top_k)

    def get_stats(self) -> Dict:
        stats = self._engine.get_stats()
        stats["version"] = "v2"
        return stats

    def reload(self) -> Dict:
        return self._engine.reload()

    def health_check(self) -> Dict:
        return {"name": "skill_matrix_v2", "status": "healthy"}


skill_matrix_v2_engine = SkillMatrixV2Engine()
