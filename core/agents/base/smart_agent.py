#!/usr/bin/env python3
"""Smart Agent v4.0 - 精简基类，智能委托给 AgentCortex

v4.0 改动：
- 删除所有 LLM 调用（can_handle, should_delegate, decompose_task, classify）
- 删除 handle() 智能入口（由 AgentCortex 替代）
- 保留：配置加载、Mixins、经验记录、统计
- 新增：直接委托给 AgentCortex 的快捷方法
"""

import time
from abc import abstractmethod
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.agents.base.communicable_agent import CommunicableAgent
from core.agents.base.mixins.config_mixin import ConfigMixin
from core.agents.base.mixins.lifecycle_mixin import LifecycleMixin
from core.agents.base.mixins.memory_mixin import MemoryMixin
from core.lib.unified_config import unified_config


class SmartAgent(CommunicableAgent, LifecycleMixin, ConfigMixin, MemoryMixin):
    """精简智能基类 - 智能委托给 AgentCortex"""

    name = "smart_agent"
    description = "智能体基类"
    type = "core"
    version = "4.0.0"

    def __init__(self, user_id: str = "default") -> None:
        super().__init__(user_id=user_id)

        self.birth_time = datetime.now()
        self._capability_descriptions: List[str] = []
        self._capability_scores: Dict[str, float] = defaultdict(lambda: 0.5)

        self.experiences: List[Dict] = []
        self._performance_stats = {
            "total_tasks": 0,
            "success_count": 0,
            "avg_response_time": 0.0,
            "learning_iterations": 0,
        }

        self.confidence_threshold = 0.6
        self.learning_rate = 0.1
        self.max_retries = 2

        self._load_intelligent_config()
        self._init_memory_dir()
        self._init_lifecycle()
        self._load_config()
        self._load_memory()

        print(f"[{self.name}] SmartAgent v{self.version} 初始化")

    # ==================== 核心入口（子类实现） ====================

    @abstractmethod
    def process(self, user_input: str, context: dict = None) -> dict:
        """处理用户输入 - 子类实现具体业务逻辑"""
        pass

    def handle(self, user_input: str, context: dict = None) -> dict:
        """兼容旧接口 - 直接委托给 process"""
        return self.process(user_input, context)

    # ==================== 自我认知（供 AgentCortex 查询，不调LLM） ====================

    def know_thyself(self) -> Dict:
        """自知之明 - 纯数据，不调LLM"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capability_descriptions": self._capability_descriptions,
            "capability_scores": dict(self._capability_scores),
            "specialties": self._get_specialties(),
            "limitations": self._get_limitations(),
            "experience_count": len(self.experiences),
            "success_rate": self._get_success_rate(),
        }

    def can_handle(self, user_input: str, context: Dict = None) -> Dict:
        """快速判断（不调LLM）- 基于关键词+历史成功率"""
        score = self._get_historical_success_rate(user_input)

        # 关键词加分
        for cap in self._capability_descriptions:
            if isinstance(cap, str) and cap.lower() in user_input.lower():
                score = min(1.0, score + 0.2)

        return {
            "can": score > self.confidence_threshold,
            "confidence": score,
            "reason": "基于历史+关键词",
            "capability_match": score,
            "historical_success": self._get_success_rate(),
        }

    # ==================== 学习（保留，不调LLM） ====================

    def learn_from_experience(self, experience: Dict) -> None:
        """从经验中学习"""
        self.experiences.append(experience)

        task_type = experience.get("task_type", "unknown")
        success = experience.get("success", False)
        self._success_history[task_type].append(1 if success else 0)

        if len(self._success_history[task_type]) > 100:
            self._success_history[task_type] = self._success_history[task_type][-100:]

        if "capability_used" in experience:
            cap = experience["capability_used"]
            current = self._capability_scores[cap]
            adjustment = self.learning_rate * (1 if success else -0.5)
            self._capability_scores[cap] = max(0.0, min(1.0, current + adjustment))

        self._performance_stats["learning_iterations"] += 1

    def record_experience(self, experience: Dict) -> None:
        """记录经验"""
        experience["timestamp"] = datetime.now().isoformat()
        self.experiences.append(experience)
        if len(self.experiences) > 100:
            self.experiences = self.experiences[-100:]

    def reflect_on_result(self, result: Dict) -> Dict:
        """反思结果（纯规则，不调LLM）"""
        reflection = {
            "success": result.get("success", False),
            "score": 0,
            "strengths": [],
            "weaknesses": [],
            "improvements": [],
        }

        if result.get("success"):
            reflection["score"] += 60
            reflection["strengths"].append("任务完成")

        response_time = result.get("response_time", 0)
        if response_time < 1000:
            reflection["score"] += 20
            reflection["strengths"].append("响应快速")
        elif response_time > 5000:
            reflection["weaknesses"].append("响应较慢")

        if result.get("accuracy", 1.0) > 0.8:
            reflection["score"] += 20
            reflection["strengths"].append("准确度高")

        if reflection["score"] < 70:
            reflection["improvements"].append("考虑优化策略")

        return reflection

    def optimize_self(self) -> Dict:
        """自我优化 - 基于历史表现调整参数"""
        success_rate = self._get_success_rate()
        optimizations = {}

        if success_rate > 0.8:
            old = self.confidence_threshold
            self.confidence_threshold = min(0.8, old + 0.05)
            optimizations["confidence_threshold"] = {"old": old, "new": self.confidence_threshold}
        elif success_rate < 0.5:
            old = self.confidence_threshold
            self.confidence_threshold = max(0.4, old - 0.05)
            optimizations["confidence_threshold"] = {"old": old, "new": self.confidence_threshold}

        if self._performance_stats["learning_iterations"] > 50:
            self.learning_rate = max(0.05, self.learning_rate * 0.95)
            optimizations["learning_rate"] = {"new": self.learning_rate}

        return optimizations

    # ==================== 辅助 ====================

    def _get_specialties(self) -> List[str]:
        return [cap for cap, score in self._capability_scores.items() if score > 0.7]

    def _get_limitations(self) -> List[str]:
        return [cap for cap, score in self._capability_scores.items() if score < 0.3]

    def _get_success_rate(self) -> float:
        total = self._performance_stats.get("total_tasks", 0)
        if total == 0:
            return 0.5
        return self._performance_stats.get("success_count", 0) / total

    def _get_historical_success_rate(self, user_input: str) -> float:
        """基于历史的成功率估计"""
        return self._get_success_rate()

    def register_capability(self, capability: str, initial_score: float = 0.5):
        if capability not in self._capability_descriptions:
            self._capability_descriptions.append(capability)
        self._capability_scores[capability] = initial_score

    def get_stats(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "total_tasks": self._performance_stats.get("total_tasks", 0),
            "success_rate": self._get_success_rate(),
            "avg_response_time": self._performance_stats.get("avg_response_time", 0),
            "experience_count": len(self.experiences),
            "capabilities": self._capability_descriptions,
            "specialties": self._get_specialties(),
        }

    def get_memory(self, key: str, default=None) -> Any:
        return self._memory.get(key, default)

    def set_memory(self, key: str, value) -> None:
        self._memory[key] = value

    def _load_intelligent_config(self):
        self.confidence_threshold = unified_config.get("smart.confidence_threshold", 0.6)
        self.learning_rate = unified_config.get("smart.learning_rate", 0.1)
        self.max_retries = unified_config.get("smart.max_retries", 2)
