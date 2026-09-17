#!/usr/bin/env python3
"""Decision Evaluator - Decision Evaluator 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""决策评估器 - 配置驱动版"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

from core.lib.gray_executor import gray_executor
from core.lib.path_manager import path_manager
from core.lib.rollback_manager import rollback_manager


class DecisionEvaluator:
    def __init__(self):
        self._load_config()
        self.history_file = path_manager.get_absolute("data.decision_history")
        self._load_history()

    def _load_config(self):
        config_file = Path(__file__).parent.parent / "config/decision.yaml"
        if config_file.exists():
            with open(config_file, "r") as f:
                self.config = unified_config.get("decision_evaluator", {})
        else:
            self.config = {"risk": {"levels": {}}, "execution": {}}

    def _load_history(self):
        if self.history_file.exists():
            with open(self.history_file, "r") as f:
                self.history = json.load(f)
        else:
            self.history = {"decisions": [], "stats": {"total": 0, "success": 0}}

    def _save_history(self):
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.history_file, "w") as f:
            json.dump(self.history, f, indent=2)

    def evaluate(self, suggestion: str) -> Dict:
        """评估建议 - 完全配置驱动"""
        risk_level, risk_keyword = self._detect_risk(suggestion)
        risk_config = self.config["risk"]["levels"].get(risk_level, {})

        # 查找相似历史
        similar = self._find_similar(suggestion)
        success_rate = sum(1 for s in similar if s.get("success")) / max(
            1, len(similar)
        )

        # 决策
        action = risk_config.get("action", "allow")
        require_confirm = risk_config.get("require_confirm", False)

        auto_levels = self.config["execution"].get("auto_execute_levels", ["low"])
        should_execute = risk_level in auto_levels

        return {
            "suggestion": suggestion,
            "risk_level": risk_level,
            "risk_keyword": risk_keyword,
            "action": action,
            "require_confirm": require_confirm,
            "should_execute": should_execute,
            "success_rate": success_rate,
            "similar_count": len(similar),
            "reason": f"风险等级: {risk_level}, 操作: {action}",
        }

    def _detect_risk(self, suggestion: str) -> Tuple[str, str]:
        """检测风险等级"""
        suggestion_lower = suggestion.lower()

        for level, config in self.config["risk"]["levels"].items():
            for keyword in config.get("keywords", []):
                if keyword in suggestion_lower:
                    return level, keyword

        return "low", ""

    def _find_similar(self, suggestion: str, limit: int = 10) -> List[Dict]:
        similar = []
        keywords = suggestion.split()[:3]
        for decision in self.history["decisions"][-200:]:
            if any(kw in decision["suggestion"] for kw in keywords):
                similar.append(decision)
        return similar[-limit:]

    def record(self, suggestion: str, result: Dict):
        self.history["decisions"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "suggestion": suggestion[:200],
                "success": result.get("success", False),
                "execution_time": result.get("execution_time", 0),
            }
        )
        self.history["stats"]["total"] += 1
        if result.get("success"):
            self.history["stats"]["success"] += 1

        max_size = self.config.get("learning", {}).get("history_size", 500)
        if len(self.history["decisions"]) > max_size:
            self.history["decisions"] = self.history["decisions"][-max_size:]
        self._save_history()

    def reload(self):
        """热重载配置"""
        self._load_config()


decision_evaluator = DecisionEvaluator()
