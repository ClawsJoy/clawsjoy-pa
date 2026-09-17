"""强化学习引擎 - 从交互中学习最优策略"""

import json
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from engine.lib.logger import engine_logger


class ReinforcementEngine:
    def __init__(self):
        self.q_table = defaultdict(lambda: defaultdict(float))
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.epsilon = 0.1
        self.learning_log = Path("data/rl_learning.json")
        self._load()
        engine_logger.get().info("🤖 强化学习引擎已初始化")

    def _load(self):
        if self.learning_log.exists():
            with open(self.learning_log, "r") as f:
                data = json.load(f)
                self.q_table = defaultdict(lambda: defaultdict(float))
                for k, v in data.get("q_table", {}).items():
                    self.q_table[k] = defaultdict(float, v)

    def _save(self):
        with open(self.learning_log, "w") as f:
            json.dump(
                {"q_table": {k: dict(v) for k, v in self.q_table.items()}}, f, indent=2
            )

    def get_action(self, state: str, available_actions: List[str]) -> str:
        if random.random() < self.epsilon:
            return random.choice(available_actions)
        # 确保状态存在
        if state not in self.q_table:
            self.q_table[state] = defaultdict(float)
        q_values = {action: self.q_table[state][action] for action in available_actions}
        return max(q_values, key=q_values.get)

    def update(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str,
        next_actions: List[str],
    ):
        # 确保状态存在
        if state not in self.q_table:
            self.q_table[state] = defaultdict(float)
        if next_state not in self.q_table:
            self.q_table[next_state] = defaultdict(float)

        old_q = self.q_table[state][action]
        # 安全获取 future_q
        if next_actions:
            future_q = max([self.q_table[next_state].get(a, 0) for a in next_actions])
        else:
            future_q = 0
        new_q = old_q + self.learning_rate * (
            reward + self.discount_factor * future_q - old_q
        )
        self.q_table[state][action] = new_q
        self._save()

    def process(self, input_data: Any = None, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, str):
            return self.get_action(input_data, kwargs.get("actions", ["chat_agent"]))
        if isinstance(input_data, dict):
            action = input_data.get("action", "get_action")
            if action == "update":
                return self.update(
                    input_data.get("state", ""),
                    input_data.get("action", ""),
                    input_data.get("reward", 0),
                    input_data.get("next_state", ""),
                    input_data.get("next_actions", []),
                )
            return self.get_action(
                input_data.get("state", ""), input_data.get("actions", ["chat_agent"])
            )
        return self.get_stats()

    def get_stats(self) -> Dict:
        return {"q_table_size": len(self.q_table), "epsilon": self.epsilon}


rl_engine = ReinforcementEngine()
