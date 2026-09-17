"""增强语义理解引擎 - 使用本地向量"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from engine.embedding.local_embedding import local_embedding
from engine.lib.logger import engine_logger


class EnhancedSemanticEngine:
    """增强语义理解引擎"""

    def __init__(self):
        self.context_memory = {}
        self.embedding = local_embedding
        engine_logger.get().info("🧠 增强语义理解引擎已初始化 (本地向量)")

    def understand_with_context(
        self, text: str, user_id: str, conversation_history: List[Dict] = None
    ) -> Dict:
        """带上下文的语义理解"""
        # 1. 基础意图识别
        base_intent = self._base_intent(text)

        # 2. 向量相似度增强
        similar_intents = self._find_similar_intents(text)

        # 3. 上下文增强
        if conversation_history:
            context = self._extract_context(conversation_history)
            base_intent["context"] = context

        # 4. 用户画像增强
        user_context = self.context_memory.get(user_id, {})
        base_intent["user_context"] = user_context

        # 5. 置信度计算
        confidence = self._calculate_confidence(base_intent, conversation_history)
        base_intent["confidence"] = confidence
        base_intent["similar_intents"] = similar_intents

        # 6. 存储上下文
        self._update_context(user_id, text, base_intent)

        return base_intent

    def _base_intent(self, text: str) -> Dict:
        intents = {
            "download": ["下载视频", "保存视频", "youtube下载", "下载YouTube", "下载"],
            "greeting": ["你好", "您好", "hi", "hello"],
            "query": ["什么", "如何", "为什么", "哪个"],
            "action": ["帮我", "请", "需要", "想要"],
        }

        for intent, keywords in intents.items():
            if any(kw in text for kw in keywords):
                return {"intent": intent, "entities": self._extract_entities(text)}

        return {"intent": "unknown", "entities": {}}

    def _find_similar_intents(self, text: str) -> List[Dict]:
        """基于向量查找相似意图 - 从配置动态加载"""
        # 从 unified_config 加载意图示例
        intent_examples = self._load_intent_examples()

        results = []
        for intent, examples in intent_examples.items():
            if not examples:
                continue
            try:
                best_sim = max(self.embedding.similarity(text, ex) for ex in examples)
                if best_sim > 0.3:
                    results.append({"intent": intent, "similarity": best_sim})
            except Exception as e:
                continue

        return sorted(results, key=lambda x: -x["similarity"])[:5]

    def _load_intent_examples(self) -> Dict:
        """从 keywords.yaml 加载意图示例"""
        try:
            from core.lib.unified_config import unified_config

            intents = unified_config.get("keywords.intents", {})
            intent_examples = {}
            for intent_name, intent_config in intents.items():
                keywords = intent_config.get("keywords", [])
                if keywords:
                    intent_examples[intent_name] = keywords[
                        :10
                    ]  # 取前10个关键词作为示例
            # 添加 code 意图（如果不存在）
            if "code" not in intent_examples:
                intent_examples["code"] = [
                    "写代码",
                    "编程",
                    "python",
                    "java",
                    "javascript",
                    "函数",
                    "算法",
                ]
            if "weather" not in intent_examples:
                intent_examples["weather"] = [
                    "天气",
                    "气温",
                    "温度",
                    "预报",
                    "下雨",
                    "晴天",
                ]
            if "translate" not in intent_examples:
                intent_examples["translate"] = [
                    "翻译",
                    "译成",
                    "translate",
                    "英文怎么说",
                ]
            if "calculate" not in intent_examples:
                intent_examples["calculate"] = [
                    "计算",
                    "加",
                    "减",
                    "乘",
                    "除",
                    "等于",
                    "帮我算",
                    "算一下",
                    "求值",
                    "运算",
                    "等于多少",
                ]
            if "greeting" not in intent_examples:
                intent_examples["greeting"] = ["你好", "您好", "hi", "hello", "在吗"]
            return intent_examples
        except Exception as e:
            print(f"加载意图示例失败: {e}")
            return {
                "code": ["写代码", "编程", "python"],
                "weather": ["天气", "气温"],
                "translate": ["翻译", "译成"],
                "calculate": ["计算", "加", "减"],
                "greeting": ["你好", "您好"],
            }

    def _load_intent_examples(self) -> Dict:
        """从 keywords.yaml 加载意图示例"""
        try:
            from core.lib.unified_config import unified_config

            intents = unified_config.get("keywords.intents", {})
            intent_examples = {}
            for intent_name, intent_config in intents.items():
                keywords = intent_config.get("keywords", [])
                if keywords:
                    intent_examples[intent_name] = keywords[
                        :10
                    ]  # 取前10个关键词作为示例
            # 添加 code 意图（如果不存在）
            if "code" not in intent_examples:
                intent_examples["code"] = [
                    "写代码",
                    "编程",
                    "python",
                    "java",
                    "javascript",
                    "函数",
                    "算法",
                ]
            if "weather" not in intent_examples:
                intent_examples["weather"] = [
                    "天气",
                    "气温",
                    "温度",
                    "预报",
                    "下雨",
                    "晴天",
                ]
            if "translate" not in intent_examples:
                intent_examples["translate"] = [
                    "翻译",
                    "译成",
                    "translate",
                    "英文怎么说",
                ]
            if "calculate" not in intent_examples:
                intent_examples["calculate"] = [
                    "计算",
                    "加",
                    "减",
                    "乘",
                    "除",
                    "等于",
                    "帮我算",
                    "算一下",
                    "求值",
                    "运算",
                    "等于多少",
                ]
            if "greeting" not in intent_examples:
                intent_examples["greeting"] = ["你好", "您好", "hi", "hello", "在吗"]
            return intent_examples
        except Exception as e:
            print(f"加载意图示例失败: {e}")
            return {
                "code": ["写代码", "编程", "python"],
                "weather": ["天气", "气温"],
                "translate": ["翻译", "译成"],
                "calculate": ["计算", "加", "减"],
                "greeting": ["你好", "您好"],
            }

    def _extract_entities(self, text: str) -> Dict:
        import re

        entities = {}
        name_match = re.search(r"[我]叫([\u4e00-\u9fa5]{2,4})", text)
        if name_match:
            entities["name"] = name_match.group(1)
        num_match = re.search(r"\d+", text)
        if num_match:
            entities["number"] = num_match.group()
        return entities

    def _extract_context(self, history: List[Dict]) -> Dict:
        if not history:
            return {}
        recent = history[-5:]
        topics = [turn.get("intent", "unknown") for turn in recent]
        return {"recent_intents": topics, "conversation_length": len(history)}

    def _calculate_confidence(self, intent: Dict, history: List[Dict]) -> float:
        base = 0.7 if intent["intent"] != "unknown" else 0.3
        if history and len(history) > 0:
            base = min(base + 0.1, 0.95)
        return base

    def _update_context(self, user_id: str, text: str, intent: Dict):
        if user_id not in self.context_memory:
            self.context_memory[user_id] = {"history": [], "preferences": {}}
        self.context_memory[user_id]["history"].append(
            {"text": text, "intent": intent, "timestamp": datetime.now().isoformat()}
        )
        if len(self.context_memory[user_id]["history"]) > 50:
            self.context_memory[user_id]["history"] = self.context_memory[user_id][
                "history"
            ][-50:]

    def get_stats(self) -> Dict:
        return {
            "users": len(self.context_memory),
            "total_history": sum(
                len(u["history"]) for u in self.context_memory.values()
            ),
            "embedding_ready": True,
        }


enhanced_semantic = EnhancedSemanticEngine()
