"""主动学习闭环 - 集成到 enhanced_chat"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from engine.active import active_engine
from engine.profile import profile_engine
from engine.semantic import semantic_engine


class ActiveLearningLoop:
    """主动学习闭环"""

    def __init__(self):
        self.learned_patterns = []

    def process(
        self,
        user_id: str,
        message: str,
        response: str,
        intent: str,
        confidence: float,
        success: bool = True,
    ):
        """处理交互，触发学习"""

        # 1. 记录交互
        active_engine.record_interaction(
            user_id, message, response, success, confidence
        )

        # 2. 检查是否需要主动询问
        should_ask, uncertainty = active_engine.should_ask(message, intent, confidence)

        if should_ask and uncertainty:
            print(f"[主动学习] 不确定: {uncertainty.reasons}")
            return {
                "should_ask": True,
                "suggestion": (
                    uncertainty.suggested_questions[0]
                    if uncertainty.suggested_questions
                    else "能说得更清楚些吗？"
                ),
            }

        # 3. 低置信度时学习
        if confidence < 0.5 and success:
            self._learn_from_low_confidence(user_id, message, intent, response)

        return {"should_ask": False}

    def _learn_from_low_confidence(
        self, user_id: str, message: str, intent: str, response: str
    ):
        """从低置信度交互中学习"""
        # 记录待学习样本
        active_engine.record_interaction(user_id, message, response, True, 0.4)

        # 如果重复出现相同模式，生成规则
        pattern_key = f"{intent}:{message[:30]}"
        if pattern_key not in self.learned_patterns:
            self.learned_patterns.append(pattern_key)
        else:
            # 重复模式，生成规则
            print(f"[主动学习] 发现重复模式，建议添加规则: {message[:50]}")
            self._suggest_rule(intent, message, response)

    def _suggest_rule(self, intent: str, message: str, response: str):
        """建议添加规则"""
        print(
            f"""
        ========================================
        [主动学习] 建议添加规则
        ========================================
        意图: {intent}
        触发: "{message[:50]}"
        响应: "{response[:100]}"
        ========================================
        """
        )


# 全局实例
active_loop = ActiveLearningLoop()
