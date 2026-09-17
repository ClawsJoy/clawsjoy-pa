"""元学习引擎 - 学会如何学习"""

import json
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from engine.lib.logger import engine_logger


class MetaEngine:
    """元学习引擎"""

    def __init__(self):
        self.strategies = {
            "code": ["few_shot", "chain_of_thought", "direct", "step_by_step"],
            "translate": ["example_based", "rule_based", "direct"],
            "qa": ["retrieval", "reasoning", "direct"],
            "default": ["direct"],
        }
        self.strategy_performance = defaultdict(list)
        self.meta_file = Path("data/meta_learning.json")
        self._load()
        engine_logger.get().info("🧠 元学习引擎已初始化")

    def _load(self):
        if self.meta_file.exists():
            with open(self.meta_file, "r") as f:
                data = json.load(f)
                self.strategy_performance = defaultdict(
                    list, data.get("performance", {})
                )

    def _save(self):
        with open(self.meta_file, "w") as f:
            json.dump(
                {
                    "performance": dict(self.strategy_performance),
                    "updated_at": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

    def select_strategy(self, task_type: str) -> str:
        """选择最佳学习策略"""
        available = self.strategies.get(task_type, self.strategies["default"])

        # 计算每个策略的得分
        scores = {}
        for strategy in available:
            perf = self.strategy_performance.get(f"{task_type}:{strategy}", [])
            if perf:
                scores[strategy] = sum(perf[-10:]) / len(perf[-10:])
            else:
                scores[strategy] = 0.5  # 默认得分

        if not scores:
            return available[0]

        # 探索 vs 利用
        if random.random() < 0.2:  # 20% 探索
            return random.choice(available)

        return max(scores, key=scores.get)

    def record_outcome(
        self, task_type: str, strategy: str, success: bool, latency_ms: float = 0
    ):
        """记录策略执行结果"""
        score = 1.0 if success else 0.0
        score = score * (1 - min(latency_ms / 10000, 0.3))  # 延迟惩罚

        self.strategy_performance[f"{task_type}:{strategy}"].append(score)

        # 保留最近100条
        if len(self.strategy_performance[f"{task_type}:{strategy}"]) > 100:
            self.strategy_performance[f"{task_type}:{strategy}"] = (
                self.strategy_performance[f"{task_type}:{strategy}"][-100:]
            )

        self._save()
        engine_logger.get().debug(f"   📊 策略 {strategy} 得分: {score:.2f}")

    def get_best_strategy(self, task_type: str) -> str:
        """获取最佳策略"""
        scores = {}
        for strategy in self.strategies.get(task_type, []):
            perf = self.strategy_performance.get(f"{task_type}:{strategy}", [])
            scores[strategy] = sum(perf) / len(perf) if perf else 0.5
        return max(scores, key=scores.get) if scores else "direct"

    def process(self, input_data: Any = None, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, str):
            return self.select_strategy(input_data)
        if isinstance(input_data, dict):
            action = input_data.get("action", "select")
            if action == "select":
                return self.select_strategy(input_data.get("task_type", "code"))
            elif action == "record":
                return self.record_outcome(
                    input_data.get("task_type", ""),
                    input_data.get("strategy", ""),
                    input_data.get("success", True),
                    input_data.get("latency_ms", 0),
                )
        return self.get_stats()

    def get_stats(self) -> Dict:
        return {
            "tracked_strategies": len(self.strategy_performance),
            "task_types": list(self.strategies.keys()),
        }


meta_engine = MetaEngine()
