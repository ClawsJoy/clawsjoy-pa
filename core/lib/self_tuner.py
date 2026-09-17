#!/usr/bin/env python3
"""Self Tuner - Self Tuner 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""自调优器 - 参数自动优化"""
import random
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

from core.lib.closed_loop_config import closed_loop_config
from core.lib.memory_vector import vector_memory


class SelfTuner:
    """自调优器"""

    def __init__(self):
        self._load_config()
        self.history = []
        self.best_params = {}
        self.best_score = 0

    def _load_config(self):
        config_file = Path(__file__).parent.parent / "config/self_tuning.yaml"
        if config_file.exists():
            with open(config_file, "r") as f:
                self.config = unified_config.get("self_tuner", {})
        else:
            self.config = {"tunable_params": [], "strategy": {}}

    def suggest_params(self) -> Dict:
        """建议下一组参数"""
        params = {}
        for param in self.config.get("tunable_params", []):
            if self.history:
                # 基于历史优化
                params[param["path"]] = self._optimize_param(param)
            else:
                # 初始随机
                params[param["path"]] = random.uniform(
                    param["range"][0], param["range"][1]
                )
        return params

    def _optimize_param(self, param: Dict) -> float:
        """优化单个参数"""
        # 分析历史中该参数的影响
        scores = []
        for h in self.history[-50:]:
            if param["path"] in h["params"]:
                scores.append((h["params"][param["path"]], h["score"]))

        if not scores:
            return random.uniform(param["range"][0], param["range"][1])

        # 找最佳值附近
        best = max(scores, key=lambda x: x[1])
        new_val = best[0] + random.uniform(-param["step"], param["step"])
        return max(param["range"][0], min(param["range"][1], new_val))

    def evaluate(self, params: Dict) -> float:
        """评估参数效果"""
        score = 0
        weights = {
            obj["name"]: obj.get("weight", 1)
            for obj in self.config.get("objectives", [])
        }

        # 这里根据实际指标计算
        # 模拟：从最近记忆中获取指标
        metrics = self._get_metrics()

        for name, weight in weights.items():
            if name == "success_rate":
                score += weight * metrics.get("success_rate", 0.9)
            elif name == "response_time":
                rt = metrics.get("response_time", 1.0)
                score += weight * (1 / (rt + 0.1))
            elif name == "accuracy":
                score += weight * metrics.get("accuracy", 0.85)

        return min(1.0, score)

    def _get_metrics(self) -> Dict:
        """获取当前指标"""
        # 从向量记忆获取
        results = vector_memory.search("performance metrics", category="metrics", n=10)
        return {"success_rate": 0.92, "response_time": 0.8, "accuracy": 0.88}

    def record(self, params: Dict, score: float):
        """记录调优结果"""
        self.history.append(
            {"timestamp": datetime.now().isoformat(), "params": params, "score": score}
        )

        if score > self.best_score:
            self.best_score = score
            self.best_params = params.copy()

            # 存储到记忆
            vector_memory.add(
                text=f"最佳参数: {params} | 得分: {score:.3f}",
                category="tuning_result",
                metadata={"score": score},
            )

        # 保留最近500条
        if len(self.history) > 500:
            self.history = self.history[-500:]

    def get_best(self) -> Dict:
        """获取最佳参数"""
        return self.best_params or self.suggest_params()

    def apply_params(self, params: Dict):
        """应用参数到配置"""
        # 更新配置文件
        for path, value in params.items():
            self._update_config(path, value)

        # 通知热重载
        from core.lib.closed_loop_config import closed_loop_config

        closed_loop_config.reload()

    def _update_config(self, path: str, value: float):
        """更新配置"""
        # 简化的配置更新
        print(f"更新配置: {path} = {value:.3f}")


self_tuner = SelfTuner()
