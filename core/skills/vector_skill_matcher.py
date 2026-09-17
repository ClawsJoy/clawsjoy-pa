#!/usr/bin/env python3
"""Vector Skill Matcher - Vector Skill Matcher 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from core.lib.vector_knowledge_center import vector_knowledge_center


class VectorSkillMatcher:
    """用向量匹配技能，不依赖关键词"""

    # 技能向量库
    SKILL_VECTORS = {
        "weather": "查询天气、气温、温度、会不会下雨、今天热吗、明天冷吗",
        "dialect": "方言、粤语、宁波话、上海话、四川话、怎么说、用XX说",
        "translate": "翻译、译成、英文怎么说、中文意思、英译中、中译英",
        "calculate": "计算、加、减、乘、除、等于、多少、算术",
        "datetime": "时间、几点、日期、今天、星期几、现在",
        "random": "随机数、随机、抽一个、随便选",
        "convert": "换算、转换、厘米、米、公里、千克、斤、两",
        "location": "在哪里、位置、城市、宁波、北京、上海",
        "memory": "记住、忘记、回忆、我叫、我在",
    }

    @classmethod
    def match(cls, user_input: str) -> str:
        """向量匹配最合适的技能"""
        try:
            # 使用向量检索
            collection = vector_knowledge_center._get_collection("skill_vectors")
            if not collection:
                return cls._keyword_match(user_input)

            results = collection.query(query_texts=[user_input], n_results=1)
            if results and results.get("ids") and results["ids"][0]:
                metadata = results["metadatas"][0][0]
                return metadata.get("skill", "chat")
        except Exception as e:
            pass
        return cls._keyword_match(user_input)

    @classmethod
    def _keyword_match(cls, user_input: str) -> str:
        """关键词兜底"""
        user_lower = user_input.lower()
        for skill, keywords in cls.SKILL_VECTORS.items():
            for kw in keywords.split("、"):
                if kw in user_lower:
                    return skill
        return "chat"

    @classmethod
    def init_vectors(cls):
        """初始化技能向量库"""
        collection = vector_knowledge_center._get_or_create_collection("skill_vectors")
        for skill, desc in cls.SKILL_VECTORS.items():
            collection.upsert(
                ids=[f"skill_{skill}"],
                documents=[desc],
                metadatas=[{"skill": skill, "description": desc}],
            )
        print(f"✅ 已初始化 {len(cls.SKILL_VECTORS)} 个技能向量")


vector_matcher = VectorSkillMatcher()
