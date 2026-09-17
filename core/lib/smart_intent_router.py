"""智能意图路由器 - 集成语义引擎"""

from typing import Dict, Optional

from core.lib.agent_intent_router import smart_route as keyword_route
from engine.semantic import semantic_engine


class SmartIntentRouter:
    """智能路由器 - 语义理解 + 关键词兜底"""

    # 语义意图到 Agent 的映射
    # 从配置文件加载意图映射（配置驱动）
    INTENT_TO_AGENT = {
        "calculate": "calculator_agent",
        "weather": "weather_skill",
        "translate": "translate_agent",
        "code": "code_agent",
        "analysis": "analysis_agent",
        "dialect": "dialect_agent",
        "video": "video_agent",
        "chat": "chat_agent",
        "greeting": "chat_agent",
        "farewell": "chat_agent",
    }

    @classmethod
    def reload_config(cls):
        """重新加载配置"""
        from pathlib import Path

        import yaml

        config_path = Path("config/intent_agent_map.yaml")
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                cls.INTENT_TO_AGENT = config.get("intent_to_agent", {})
        return cls.INTENT_TO_AGENT

    def route(self, message: str) -> Dict:
        """智能路由：先语义理解，再关键词兜底"""

        # 1. 语义理解
        try:
            semantic_result = semantic_engine.understand(message)
            intent = semantic_result.intent
            confidence = semantic_result.confidence

            # 高置信度直接使用语义结果
            if confidence > 0.7:
                agent = self.INTENT_TO_AGENT.get(intent)
                if agent:
                    return {
                        "agent": agent,
                        "source": "semantic",
                        "intent": intent,
                        "confidence": confidence,
                        "original_message": message,
                    }
        except Exception as e:
            print(f"语义引擎错误: {e}")

        # 2. 关键词兜底
        agent = keyword_route(message)
        return {
            "agent": agent,
            "source": "keyword",
            "intent": None,
            "confidence": 0,
            "original_message": message,
        }


smart_intent_router = SmartIntentRouter()


def smart_intent_route(message: str) -> str:
    """智能路由函数"""
    return smart_intent_router.route(message)["agent"]
