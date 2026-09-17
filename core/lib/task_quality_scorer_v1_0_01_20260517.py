#!/usr/bin/env python3
"""Task Quality Scorer V1 0 01 20260517 - Task Quality Scorer V1 0 01 20260517 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""任务质量评分器 v1.0.01 - 配置驱动版"""

from pathlib import Path
from typing import Dict, Tuple

from core.lib.config_driver_v1_0_00_20260517 import config_driver
from core.lib.unified_config import unified_config


class TaskQualityScorer:
    """任务质量评分器 - 配置驱动版"""

    VERSION = "1.0.01"

    def __init__(self):
        self.min_score = config_driver.get("thresholds.quality_min_score", 0.5)
        self.enabled = config_driver.get("optimization.enable_quality_scoring", True)

    def score(self, task_name: str, skill: str = "", params: Dict = None) -> Dict:
        if not self.enabled:
            return {"score": 1.0, "should_skip": False, "reasons": ["评分器已禁用"]}

        params = params or {}
        score = 1.0
        reasons = []

        # 检查输入文件
        if params.get("input_file"):
            file_path = Path(params["input_file"])
            if not file_path.exists():
                score -= 0.5
                reasons.append(f"输入文件不存在: {params['input_file']}")

        # 检查低质量关键词
        low_quality = ["test", "debug", "temp", "demo"]
        if any(kw in task_name.lower() for kw in low_quality):
            score -= 0.2
            reasons.append("任务名称包含低质量关键词")

        score = max(0.0, min(1.0, score))
        should_skip = score < self.min_score

        return {
            "task": task_name,
            "skill": skill,
            "score": round(score, 2),
            "should_skip": should_skip,
            "reasons": reasons,
            "min_threshold": self.min_score,
            "enabled": self.enabled,
            "version": self.VERSION,
        }


quality_scorer = TaskQualityScorer()
