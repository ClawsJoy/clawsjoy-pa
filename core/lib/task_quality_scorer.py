#!/usr/bin/env python3
"""Task Quality Scorer - Task Quality Scorer 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""任务质量评分器 v1.0.02 - 配置驱动版"""

from pathlib import Path
from typing import Any, Dict

from core.lib.config_loader import config


class TaskQualityScorer:
    """任务质量评分器 - 配置驱动"""

    VERSION = "1.0.02"

    def __init__(self):
        self.enabled = config.get("optimization.enable_quality_scoring", True)
        self.min_score = config.get("thresholds.quality_min_score", 0.5)
        self.skip_on_low = config.get("optimization.skip_on_low_quality", True)
        self.low_quality_keywords = ["test", "debug", "temp", "demo", "tmp"]

    def score(self, task_name: str, skill: str = "", params: Dict = None) -> Dict:
        if not self.enabled:
            return {
                "score": 1.0,
                "should_skip": False,
                "reasons": ["评分器已禁用"],
                "enabled": False,
            }

        params = params or {}
        score = 1.0
        reasons = []

        if params.get("input_file"):
            file_path = Path(params["input_file"])
            if not file_path.exists():
                score -= 0.5
                reasons.append(f"输入文件不存在: {params['input_file']}")

        if any(kw in task_name.lower() for kw in self.low_quality_keywords):
            score -= 0.2
            reasons.append("任务名称包含低质量关键词")

        score = max(0.0, min(1.0, score))
        should_skip = self.skip_on_low and score < self.min_score

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

    def get_status(self) -> Dict:
        return {
            "version": self.VERSION,
            "enabled": self.enabled,
            "min_score": self.min_score,
            "skip_on_low": self.skip_on_low,
        }


quality_scorer = TaskQualityScorer()


if __name__ == "__main__":
    print(f"质量评分器 v{quality_scorer.VERSION}")
    result = quality_scorer.score("测试任务", "test_skill", {})
    print(f"测试: {result}")
