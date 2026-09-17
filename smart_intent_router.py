"""智能意图路由器 - 关键词路由"""

from typing import Dict, Optional

from core.lib.agent_intent_router import smart_route as keyword_route


class SmartIntentRouter:
    """智能路由器 - 关键词路由"""

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
        """智能路由：关键词兜底"""

        # 关键词兜底
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
