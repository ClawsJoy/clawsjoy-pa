"""技能引擎 - skill_matrix 的代理"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from engine.skill_matrix.core import skill_matrix_engine


class SkillEngine:
    """技能引擎 - 统一技能管理入口"""

    def __init__(self):
        self._engine = skill_matrix_engine

    def process(self, input_data: Any = None, **kwargs) -> Any:
        return self._engine.process(input_data, **kwargs)

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        return self._engine.search(query, top_k)

    def search_skills(self, query: str, top_k: int = 5) -> List[Dict]:
        return self.search(query, top_k)

    def get_stats(self) -> Dict:
        return self._engine.get_stats()

    def reload(self) -> Dict:
        return self._engine.reload()

    def health_check(self) -> Dict:
        return {"name": "skill_engine", "status": "healthy", "backend": "skill_matrix"}


skill_engine = SkillEngine()
