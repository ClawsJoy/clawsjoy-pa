from pathlib import Path

"""自主进化引擎 - 引擎自我优化和演进"""

import json
import random
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from engine.lib.logger import engine_logger


class AutonomousEvolutionEngine:
    """自主进化引擎"""

    def __init__(self):
        self.evolution_log = Path("data/evolution_log.json")
        self.mutations = []
        self.performance_history = []
        self._load()
        engine_logger.get().info("🧬 自主进化引擎已初始化")

    def _load(self):
        if self.evolution_log.exists():
            with open(self.evolution_log, "r") as f:
                data = json.load(f)
                self.mutations = data.get("mutations", [])
                self.performance_history = data.get("performance_history", [])

    def _save(self):
        with open(self.evolution_log, "w") as f:
            json.dump(
                {
                    "mutations": self.mutations[-100:],
                    "performance_history": self.performance_history[-100:],
                    "updated_at": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

    def mutate(self, component: str, current_value: Any) -> Dict:
        """变异 - 尝试优化参数"""
        mutation_types = ["increase", "decrease", "toggle", "replace"]
        mutation_type = random.choice(mutation_types)

        new_value = current_value
        if mutation_type == "increase" and isinstance(current_value, (int, float)):
            new_value = current_value * (1 + random.uniform(0.05, 0.2))
        elif mutation_type == "decrease" and isinstance(current_value, (int, float)):
            new_value = current_value * (1 - random.uniform(0.05, 0.2))
        elif mutation_type == "toggle" and isinstance(current_value, bool):
            new_value = not current_value

        mutation = {
            "component": component,
            "old_value": current_value,
            "new_value": new_value,
            "type": mutation_type,
            "timestamp": datetime.now().isoformat(),
            "applied": True,
        }
        self.mutations.append(mutation)
        self._save()

        engine_logger.get().info(f"   🧬 变异: {component} → {new_value}")
        return {"success": True, "mutation": mutation}

    def evaluate(self, metric: str, value: float) -> Dict:
        """评估性能"""
        self.performance_history.append(
            {"metric": metric, "value": value, "timestamp": datetime.now().isoformat()}
        )
        self._save()

        # 分析趋势
        recent = [h for h in self.performance_history[-10:] if h["metric"] == metric]
        if len(recent) >= 5:
            avg = sum(h["value"] for h in recent) / len(recent)
            trend = "improving" if recent[-1]["value"] > avg else "declining"
            return {"trend": trend, "average": avg, "current": value}

        return {"trend": "unknown", "current": value}

    def get_evolution_stats(self) -> Dict:
        """获取进化统计"""
        return {
            "total_mutations": len(self.mutations),
            "performance_history": len(self.performance_history),
            "recent_mutations": self.mutations[-5:],
            "status": "active",
        }

    def process(self, input_data: Any = None, **kwargs) -> Any:
        if input_data is None:
            return self.get_evolution_stats()
        if isinstance(input_data, dict):
            action = input_data.get("action", "mutate")
            if action == "mutate":
                return self.mutate(
                    input_data.get("component", "unknown"), input_data.get("value")
                )
            elif action == "evaluate":
                return self.evaluate(
                    input_data.get("metric", "unknown"), input_data.get("value", 0)
                )
        return self.get_evolution_stats()

    def get_stats(self) -> Dict:
        return {"total_mutations": len(self.mutations), "status": "active"}

    def reload(self) -> Dict:
        self._load()
        return {"success": True, "message": "Evolution engine reloaded"}


evolution_engine = AutonomousEvolutionEngine()
