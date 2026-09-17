#!/usr/bin/env python3
"""智能升级器 - 带防重复机制的升级器"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

from core.agents.builtin.config_upgrader import ConfigUpgrader


class SmartUpgrader(ConfigUpgrader):
    """智能升级器 - 避免无效重复升级"""

    def __init__(self, model_name: str = "qwen2.5:7b-instruct-q4_0-gpu"):
        super().__init__(model_name)
        self.cooldown_hours = 4  # 同Agent升级冷却时间4小时
        self.min_improvement_threshold = 0.05  # 最小改进阈值5%

    def _should_skip_upgrade(
        self, agent_name: str, suggestions: Dict, current_success_rate: float
    ) -> Tuple[bool, str]:
        """检查是否应该跳过升级"""

        # 1. 如果成功率已经高于75%，跳过
        if current_success_rate >= 0.75:
            return True, f"成功率{current_success_rate:.1%}已达目标，无需升级"

        # 2. 检查冷却时间
        recent_upgrades = [
            h
            for h in self.history
            if h.get("agent") == agent_name and h.get("applied") == True
        ]

        if recent_upgrades:
            last_upgrade = datetime.fromisoformat(recent_upgrades[-1]["timestamp"])
            hours_since = (datetime.now() - last_upgrade).total_seconds() / 3600

            if hours_since < self.cooldown_hours:
                return True, f"冷却中，距上次升级仅{hours_since:.1f}小时"

        # 3. 检查配置是否已经是最优
        config_file = Path(f"agents/{agent_name}/config.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)

            current_temp = (
                config.get("agent", {}).get("llm", {}).get("temperature", 0.7)
            )
            suggested_temp = suggestions.get("temperature")

            if suggested_temp is not None:
                diff = abs(current_temp - suggested_temp)
                if diff < self.min_improvement_threshold:
                    return True, f"temperature已经是最优值 ({current_temp})，无需调整"

        return False, ""

    def upgrade_agent(
        self, agent_name: str, logs: List[Dict], auto_apply: bool = False
    ) -> Dict:
        """带智能判断的升级流程"""

        # 先分析
        analysis = self.analyze_performance(agent_name, logs)
        current_rate = analysis.get("success_rate", 0)
        suggestions = analysis.get("suggestions", {})

        # 智能判断
        should_skip, reason = self._should_skip_upgrade(
            agent_name, suggestions, current_rate
        )

        if should_skip:
            print(f"   ℹ️ {reason}")
            return {
                "upgraded": False,
                "reason": reason,
                "success_rate_before": current_rate,
                "suggestions": suggestions,
            }

        # 执行升级
        return super().upgrade_agent(agent_name, logs, auto_apply)


# 替换默认升级器
if __name__ == "__main__":
    upgrader = SmartUpgrader()

    # 测试
    logs = [{"success": i % 2 == 0} for i in range(100)]
    result = upgrader.upgrade_agent("chat_agent", logs, auto_apply=True)
    print(json.dumps(result, indent=2, ensure_ascii=False))
