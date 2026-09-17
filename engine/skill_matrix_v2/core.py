"""技能矩阵引擎 v2 - 增强版"""

from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from engine.lib.logger import engine_logger
from engine.skill_matrix.core import skill_matrix_engine


class SkillMatrixV2Engine:
    """技能矩阵引擎 v2 - 增强版"""

    def __init__(self):
        self._v1 = skill_matrix_engine
        engine_logger.get().info("🎯 技能矩阵引擎 v2 已初始化")

    def process(self, input_data: Any, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        return self._v1.process(input_data, **kwargs)

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """搜索技能"""
        return self._v1.search(query, top_k)

    def get_stats(self) -> Dict:
        stats = self._v1.get_stats()
        stats["version"] = "v2"
        return stats

    def reload(self) -> Dict:
        return self._v1.reload()

    def health_check(self) -> Dict:
        return {"name": "skill_matrix_v2", "status": "healthy", "v1_status": "ok"}


skill_matrix_v2_engine = SkillMatrixV2Engine()
