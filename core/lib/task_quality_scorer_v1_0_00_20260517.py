#!/usr/bin/env python3
"""Task Quality Scorer V1 0 00 20260517 - Task Quality Scorer V1 0 00 20260517 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""任务质量预评分 v1.0.00 - 执行前预测成功率"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.lib.error_knowledge_v1_0_00_20260517 import error_knowledge
from core.lib.memory_simple import memory
from core.lib.unified_config import unified_config


class TaskQualityScorer:
    """任务质量预评分器"""

    VERSION = "1.0.00"

    def __init__(self):
        self.root = unified_config.ROOT
        self.min_score_to_execute = 0.5  # 最低执行分数
        self.history_window = 50  # 历史任务窗口

    def _get_skill_history(self, skill_name: str) -> Dict:
        """获取技能历史成功率"""
        outcomes = memory.recall_all(category="workflow_outcome_v2")

        success = 0
        total = 0

        for outcome in outcomes[-self.history_window :]:
            if isinstance(outcome, str):
                if skill_name in outcome:
                    total += 1
                    if "success" in outcome or "✅" in outcome:
                        success += 1

        rate = success / max(total, 1)
        return {
            "skill": skill_name,
            "success_rate": rate,
            "total_attempts": total,
            "success_count": success,
        }

    def _check_error_history(self, task_name: str) -> Tuple[bool, str]:
        """检查是否有错误历史"""
        error = error_knowledge.query(task_name)
        if error:
            retry_count = error.get("retry_count", 0)
            if retry_count >= error_knowledge.max_retry_same_error:
                return True, f"历史失败 {retry_count} 次"
        return False, ""

    def _check_dependencies(self, task_params: Dict) -> Tuple[bool, str]:
        """检查依赖是否满足"""
        # 检查视频生成依赖
        if task_params.get("skill") in ["manju_maker", "video_maker"]:
            output_dir = self.root / "output"
            videos = list(output_dir.glob("*.mp4"))
            if not videos:
                return False, "没有找到可用的视频素材"

        # 检查文件依赖
        if task_params.get("input_file"):
            file_path = Path(task_params["input_file"])
            if not file_path.exists():
                return False, f"输入文件不存在: {task_params['input_file']}"

        return True, ""

    def score(self, task_name: str, skill: str = "", params: Dict = None) -> Dict:
        """
        预评分任务
        返回: score (0-1), 是否建议跳过, 原因
        """
        params = params or {}

        # 初始分
        score = 1.0
        reasons = []

        # 1. 检查错误历史 (-0.3 每重复失败)
        has_error, error_reason = self._check_error_history(task_name)
        if has_error:
            score -= 0.3
            reasons.append(error_reason)

        # 2. 检查技能历史成功率
        if skill:
            skill_history = self._get_skill_history(skill)
            if skill_history["total_attempts"] > 0:
                # 根据历史成功率调整分数
                history_score = skill_history["success_rate"]
                if history_score < 0.5:
                    score -= 0.2
                    reasons.append(f"{skill} 历史成功率 {history_score:.0%}")
                elif history_score > 0.8:
                    score += 0.1  # 奖励高成功率技能

        # 3. 检查依赖
        deps_ok, deps_reason = self._check_dependencies(params)
        if not deps_ok:
            score -= 0.5
            reasons.append(deps_reason)

        # 4. 检查任务名称关键词（启发式）
        low_quality_keywords = ["test", "debug", "temp", "deprecated"]
        if any(kw in task_name.lower() for kw in low_quality_keywords):
            score -= 0.2
            reasons.append("任务名称包含低质量关键词")

        # 限制分数范围
        score = max(0.0, min(1.0, score))

        should_skip = score < self.min_score_to_execute

        return {
            "task": task_name,
            "skill": skill,
            "score": round(score, 2),
            "should_skip": should_skip,
            "reasons": reasons,
            "min_threshold": self.min_score_to_execute,
            "version": self.VERSION,
        }

    def get_stats(self) -> Dict:
        """获取评分器统计"""
        return {
            "version": self.VERSION,
            "min_score_threshold": self.min_score_to_execute,
            "history_window": self.history_window,
        }


# 全局实例
quality_scorer = TaskQualityScorer()


if __name__ == "__main__":
    # 测试
    print("任务质量评分器 v1.0.00")

    # 测试评分
    result = quality_scorer.score("制作视频: 香港高才通", "manju_maker")
    print(f"评分结果: {result}")
