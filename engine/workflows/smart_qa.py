"""智能问答工作流 - 组合原子引擎"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engine.knowledge import knowledge_engine
from engine.profile import profile_engine
from engine.semantic import semantic_engine


class SmartQAWorkflow:
    """
    智能问答工作流 - 引擎组合示例

    引擎组合: 语义理解 → 知识图谱 → 用户画像
    """

    def __init__(self):
        self.semantic = semantic_engine
        self.knowledge = knowledge_engine
        self.profile = profile_engine
        print("🧠 智能问答工作流已初始化")

    def answer(self, question: str, user_id: str = "anonymous") -> dict:
        """回答问题"""

        # 步骤1: 语义理解 - 识别意图和提取实体
        semantic_result = self.semantic.understand(question)
        intent = semantic_result.intent.name
        entities = semantic_result.intent.entities

        # 步骤2: 知识图谱 - 查询相关知识
        kg_result = self.knowledge.query(question)

        # 步骤3: 用户画像 - 获取用户偏好
        profile = self.profile.get_or_create(user_id)

        # 步骤4: 综合生成答案
        answer = self._generate_answer(
            question=question,
            intent=intent,
            entities=entities,
            knowledge_nodes=kg_result.nodes,
            user_name=profile.name,
        )

        return {
            "question": question,
            "answer": answer,
            "intent": intent,
            "entities": entities,
            "knowledge_matches": len(kg_result.nodes),
            "confidence": semantic_result.intent.confidence,
        }

    def _generate_answer(
        self,
        question: str,
        intent: str,
        entities: dict,
        knowledge_nodes: list,
        user_name: str = None,
    ) -> str:
        """生成答案"""

        # 根据意图类型生成不同风格的答案
        if intent == "greeting":
            if user_name:
                return f"您好，{user_name}！很高兴为您服务！✨"
            return "您好！我是 ClawsJoy，很高兴为您服务！✨"

        elif intent == "name_set":
            name = entities.get("name", "")
            if name:
                return f"好的，{name}！我记住您了。✨"
            return "好的，我记住了！"

        elif intent == "preference_set":
            pref = entities.get("preference", "")
            if pref:
                return f"好的，我记住了！您喜欢{pref}。✨"
            return "好的，我记住了您的喜好！"

        elif intent == "capability":
            return "我可以帮您：\n• 记住您的名字和喜好\n• 查天气、翻译方言\n• 计算、回答问题\n• 编程帮助、创意写作"

        elif intent == "code":
            return "我可以帮您写代码！请告诉我具体需要什么功能的代码？"

        elif intent == "weather":
            city = entities.get("city", "您所在的城市")
            return f"📍 {city}的天气：晴，25°C，适合出门活动！"

        elif intent == "calculation":
            expr = entities.get("expr", "")
            if expr:
                try:
                    result = eval(expr)
                    return f"计算结果：{expr} = {result}"
                except Exception as e:
                    pass
            return "请告诉我具体的计算式子，比如'15+27'"

        elif intent == "name_query":
            if user_name:
                return f"您叫{user_name}呀！"
            return "您还没告诉我您的名字呢。您可以说'我叫XXX'告诉我哦~"

        elif intent == "preference_query":
            return "您可以根据您的喜好告诉我，比如'我喜欢喝茶'，我会记住的！"

        elif knowledge_nodes:
            # 使用知识图谱回答
            node_names = [n.name for n in knowledge_nodes[:3]]
            return f"根据我的知识，{question} 相关的概念有：{', '.join(node_names)}。需要我详细介绍吗？"

        else:
            return f"收到消息：「{question}」\n\n我可以帮您：\n• 记住您的名字和喜好\n• 查天气、翻译方言\n• 计算、回答问题"

    def get_stats(self) -> dict:
        """获取工作流统计"""
        return {
            "semantic": self.semantic.get_stats(),
            "knowledge": self.knowledge.get_stats(),
            "profile": self.profile.get_stats(),
        }


# 全局实例
smart_qa = SmartQAWorkflow()
